from __future__ import annotations

import asyncio
import base64
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from time import monotonic
from typing import Iterable, Optional, Sequence

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import Settings, settings
from ..models import Timer, TimerStatus, User
from ..schemas.timer import (
    TimerBatchTickItem,
    TimerBatchTickRequest,
    TimerBatchTickResponse,
    TimerCreate,
    TimerOut,
    TimerTickResponse,
)
from ..utils.redis import (
    RateLimitExceededError,
    TimerState,
    decode_timer_state,
    ensure_rate_limit,
    timer_finish_lock_key,
    timer_key,
)


class TimerNotFoundError(Exception):
    pass


class TimerService:
    def __init__(
        self,
        session: AsyncSession,
        redis: Redis,
        *,
        app_settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.redis = redis
        self.settings = app_settings or settings

    async def enforce_rate_limit(self, user: User, scope: str) -> None:
        try:
            await ensure_rate_limit(
                self.redis,
                identifier=f"{scope}:{user.id}",
                tokens=self.settings.rate_limit_tokens,
                period_seconds=self.settings.rate_limit_period_seconds,
            )
        except RateLimitExceededError as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(exc),
            ) from exc

    async def create_timer(self, user: User, payload: TimerCreate) -> TimerOut:
        await self.enforce_rate_limit(user, scope="timer:create")

        now = datetime.now(timezone.utc)
        timer = Timer(
            user_id=user.id,
            label=payload.label,
            duration_seconds=payload.duration_seconds,
            started_at=now,
            ends_at=now + timedelta(seconds=payload.duration_seconds),
        )
        self.session.add(timer)
        await self.session.commit()
        await self.session.refresh(timer)

        await self._persist_timer_state(timer)

        snapshot = await self._build_timer_snapshot(timer)
        return self._serialize_timer(timer, snapshot)

    async def cancel_timer(self, user: User, timer_id: str) -> TimerOut:
        await self.enforce_rate_limit(user, scope="timer:cancel")

        timer = await self._load_timer_for_user(timer_id, user.id)
        if timer.status != TimerStatus.RUNNING:
            snapshot = await self._build_timer_snapshot(timer)
            return self._serialize_timer(timer, snapshot)

        timer.mark_canceled()
        await self.session.commit()
        await self.session.refresh(timer)

        await self.redis.delete(timer_key(timer.id))
        await self.redis.delete(timer_finish_lock_key(timer.id))

        snapshot = await self._build_timer_snapshot(timer)
        return self._serialize_timer(timer, snapshot)

    async def get_timer(self, user: User, timer_id: str) -> TimerOut:
        timer = await self._load_timer_for_user(timer_id, user.id)
        snapshot = await self._build_timer_snapshot(timer)
        return self._serialize_timer(timer, snapshot)

    async def list_timers(self, user: User) -> Sequence[TimerOut]:
        result = await self.session.execute(
            select(Timer)
            .where(Timer.user_id == user.id)
            .order_by(Timer.created_at.desc())
        )
        timers = result.scalars().all()
        responses = []
        for timer in timers:
            snapshot = await self._build_timer_snapshot(timer)
            responses.append(self._serialize_timer(timer, snapshot))
        return responses

    async def timer_tick(
        self,
        timer_id: str,
        user: User,
        client_etag: Optional[str],
        wait: bool,
    ) -> TimerTickResponse:
        await self.enforce_rate_limit(user, scope="timer:tick")

        timeout = self.settings.long_poll_timeout_seconds if wait else 0.0
        interval = self.settings.long_poll_interval_seconds
        deadline = monotonic() + timeout

        while True:
            timer = await self._load_timer_for_user(timer_id, user.id)
            snapshot = await self._build_timer_snapshot(timer)

            if snapshot.etag != client_etag or not wait:
                return snapshot.to_schema()

            if monotonic() >= deadline:
                return snapshot.to_schema()

            await asyncio.sleep(interval)

    async def batch_timer_tick(
        self,
        request: TimerBatchTickRequest,
        user: User,
    ) -> TimerBatchTickResponse:
        await self.enforce_rate_limit(user, scope="timer:batch-tick")

        client_etags = request.client_etags or {}
        wait = request.wait
        timeout = request.timeout_seconds or self.settings.long_poll_timeout_seconds
        interval = self.settings.long_poll_interval_seconds
        deadline = monotonic() + (timeout if wait else 0)

        pending_timer_ids = set(request.timer_ids)
        snapshots: dict[str, TimerTickResponse] = {}
        not_modified: set[str] = set()

        while pending_timer_ids:
            for timer_id in list(pending_timer_ids):
                timer = await self._load_timer_for_user(timer_id, user.id)
                snapshot = await self._build_timer_snapshot(timer)
                etag = client_etags.get(timer_id)
                if snapshot.etag != etag or not wait:
                    snapshots[timer_id] = snapshot.to_schema()
                    pending_timer_ids.remove(timer_id)
                elif not wait:
                    not_modified.add(timer_id)
                    pending_timer_ids.remove(timer_id)

            if not pending_timer_ids or not wait:
                break

            if monotonic() >= deadline:
                not_modified.update(pending_timer_ids)
                break

            await asyncio.sleep(interval)

        response_items = [
            TimerBatchTickItem(**snapshots[timer_id].model_dump())
            for timer_id in request.timer_ids
            if timer_id in snapshots
        ]
        return TimerBatchTickResponse(
            timers=response_items,
            not_modified=sorted(not_modified),
        )

    async def _load_timer_for_user(self, timer_id: str, user_id: str) -> Timer:
        result = await self.session.execute(
            select(Timer).where(Timer.id == timer_id, Timer.user_id == user_id)
        )
        timer = result.scalar_one_or_none()
        if timer is None:
            raise TimerNotFoundError(f"Timer {timer_id} not found for user {user_id}")
        return timer

    async def _persist_timer_state(self, timer: Timer) -> None:
        if timer.status != TimerStatus.RUNNING:
            return

        ttl = max(int((timer.ends_at - datetime.now(timezone.utc)).total_seconds()), 1)
        mapping = {
            "end_ts": str(timer.ends_at.timestamp()),
            "user_id": timer.user_id,
            "label": timer.label,
            "duration_sec": str(timer.duration_seconds),
        }
        await self.redis.hset(timer_key(timer.id), mapping=mapping)
        await self.redis.expire(timer_key(timer.id), ttl)

    async def _ensure_timer_state(self, timer: Timer) -> Optional[TimerState]:
        data = await self.redis.hgetall(timer_key(timer.id))
        state = decode_timer_state(data, timer.id) if data else None

        if state is None and timer.status == TimerStatus.RUNNING:
            await self._persist_timer_state(timer)
            data = await self.redis.hgetall(timer_key(timer.id))
            state = decode_timer_state(data, timer.id) if data else None
        return state

    async def _build_timer_snapshot(self, timer: Timer) -> "TimerSnapshot":
        state = await self._ensure_timer_state(timer)
        now = datetime.now(timezone.utc)

        if timer.status == TimerStatus.RUNNING:
            if state is not None:
                remaining = state.remaining_seconds(now)
                ends_at = state.ends_at
            else:
                remaining = max(int((timer.ends_at - now).total_seconds()), 0)
                ends_at = timer.ends_at

            if remaining <= 0:
                await self._finalise_completed_timer(timer)
                await self.session.refresh(timer)
                remaining = 0
                ends_at = timer.ends_at
        else:
            remaining = 0
            ends_at = timer.ends_at

        last_modified = timer.updated_at
        etag = build_weak_etag(
            [
                timer.id,
                timer.status.value,
                str(timer.version),
                str(remaining),
            ]
        )

        return TimerSnapshot(
            timer_id=timer.id,
            status=timer.status,
            label=timer.label,
            ends_at=ends_at,
            remaining_seconds=remaining,
            last_modified=last_modified,
            etag=etag,
        )

    async def _finalise_completed_timer(self, timer: Timer) -> None:
        if timer.status != TimerStatus.RUNNING:
            return

        lock_key = timer_finish_lock_key(timer.id)
        lock_acquired = await self.redis.set(lock_key, "1", ex=30, nx=True)
        if not lock_acquired:
            # Another worker is finalising - allow it time
            await asyncio.sleep(0.1)
            return

        try:
            timer.mark_completed()
            await self.session.commit()
        finally:
            await self.redis.delete(lock_key)
            await self.redis.delete(timer_key(timer.id))

    def _serialize_timer(self, timer: Timer, snapshot: "TimerSnapshot") -> TimerOut:
        return TimerOut(
            id=timer.id,
            label=timer.label,
            duration_seconds=timer.duration_seconds,
            status=timer.status,
            started_at=timer.started_at,
            ends_at=timer.ends_at,
            completed_at=timer.completed_at,
            canceled_at=timer.canceled_at,
            remaining_seconds=snapshot.remaining_seconds,
            etag=snapshot.etag,
            last_modified=snapshot.last_modified,
        )


@dataclass(slots=True)
class TimerSnapshot:
    timer_id: str
    status: TimerStatus
    label: str
    ends_at: datetime
    remaining_seconds: int
    last_modified: datetime
    etag: str

    def to_schema(self) -> TimerTickResponse:
        return TimerTickResponse(
            id=self.timer_id,
            status=self.status,
            label=self.label,
            ends_at=self.ends_at,
            remaining_seconds=self.remaining_seconds,
            last_modified=self.last_modified,
            etag=self.etag,
        )


def build_weak_etag(parts: Iterable[str]) -> str:
    digest = hashlib.sha1("::".join(parts).encode("utf8")).digest()
    encoded = base64.urlsafe_b64encode(digest).decode("utf8").rstrip("=")
    return f'W/"{encoded}"'
