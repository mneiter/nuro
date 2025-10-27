from __future__ import annotations

from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import Settings, get_settings
from ..db import get_session
from ..models import User
from ..schemas.timer import (
    TimerBatchTickRequest,
    TimerBatchTickResponse,
    TimerCreate,
    TimerOut,
    TimerTickResponse,
)
from ..services.timers import TimerNotFoundError, TimerService

from .deps import get_current_user, get_redis_connection

router = APIRouter()


def _extract_client_etag(if_none_match: Optional[str]) -> Optional[str]:
    if not if_none_match:
        return None
    candidates = [token.strip() for token in if_none_match.split(",") if token.strip()]
    return candidates[0] if candidates else None


def _parse_if_modified_since(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _http_datetime(dt: datetime) -> str:
    return format_datetime(dt.astimezone(timezone.utc), usegmt=True)


def get_service(
    session: AsyncSession,
    redis: Redis,
    app_settings: Settings,
) -> TimerService:
    return TimerService(session, redis, app_settings=app_settings)


@router.post("", response_model=TimerOut, status_code=status.HTTP_201_CREATED)
async def start_timer(
    payload: TimerCreate,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis_connection),
    current_user: User = Depends(get_current_user),
    app_settings: Settings = Depends(get_settings),
) -> TimerOut:
    service = get_service(session, redis, app_settings)
    try:
        timer = await service.create_timer(current_user, payload)
    except TimerNotFoundError as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return timer


@router.get("", response_model=list[TimerOut])
async def list_timers(
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis_connection),
    current_user: User = Depends(get_current_user),
    app_settings: Settings = Depends(get_settings),
) -> list[TimerOut]:
    service = get_service(session, redis, app_settings)
    timers = await service.list_timers(current_user)
    return list(timers)


@router.get("/{timer_id}", response_model=TimerOut)
async def get_timer(
    timer_id: str,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis_connection),
    current_user: User = Depends(get_current_user),
    app_settings: Settings = Depends(get_settings),
) -> TimerOut:
    service = get_service(session, redis, app_settings)
    try:
        return await service.get_timer(current_user, timer_id)
    except TimerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.post("/{timer_id}/cancel", response_model=TimerOut)
async def cancel_timer(
    timer_id: str,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis_connection),
    current_user: User = Depends(get_current_user),
    app_settings: Settings = Depends(get_settings),
) -> TimerOut:
    service = get_service(session, redis, app_settings)
    try:
        return await service.cancel_timer(current_user, timer_id)
    except TimerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.get("/{timer_id}/tick", response_model=TimerTickResponse)
async def timer_tick(
    timer_id: str,
    response: Response,
    wait: bool = True,
    if_none_match: Optional[str] = Header(default=None, convert_underscores=False),
    if_modified_since: Optional[str] = Header(default=None, convert_underscores=False),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis_connection),
    current_user: User = Depends(get_current_user),
    app_settings: Settings = Depends(get_settings),
) -> TimerTickResponse:
    service = get_service(session, redis, app_settings)
    client_etag = _extract_client_etag(if_none_match)
    client_last_modified = _parse_if_modified_since(if_modified_since)

    try:
        tick = await service.timer_tick(timer_id, current_user, client_etag, wait=wait)
    except TimerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    headers = {
        "ETag": tick.etag,
        "Last-Modified": _http_datetime(tick.last_modified),
    }

    if client_etag and tick.etag == client_etag:
        raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)

    if client_last_modified and tick.last_modified <= client_last_modified:
        raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)

    response.headers.update(headers)
    return tick


@router.post("/batch/tick", response_model=TimerBatchTickResponse)
async def batch_tick(
    payload: TimerBatchTickRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis_connection),
    current_user: User = Depends(get_current_user),
    app_settings: Settings = Depends(get_settings),
) -> TimerBatchTickResponse:
    service = get_service(session, redis, app_settings)
    try:
        return await service.batch_timer_tick(payload, current_user)
    except TimerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
