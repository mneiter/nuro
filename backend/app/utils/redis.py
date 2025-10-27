from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from redis.asyncio import Redis

TIMER_KEY_TEMPLATE = "nuro:timer:{timer_id}"
TIMER_FINISH_LOCK_TEMPLATE = "nuro:timer:{timer_id}:finish-lock"
RATE_LIMIT_TEMPLATE = "nuro:rl:{key}"


async def create_redis_pool(url: str) -> Redis:
    return Redis.from_url(
        url,
        encoding="utf8",
        decode_responses=True,
    )


def timer_key(timer_id: str) -> str:
    return TIMER_KEY_TEMPLATE.format(timer_id=timer_id)


def timer_finish_lock_key(timer_id: str) -> str:
    return TIMER_FINISH_LOCK_TEMPLATE.format(timer_id=timer_id)


def rate_limit_key(identifier: str) -> str:
    return RATE_LIMIT_TEMPLATE.format(key=identifier)


async def ensure_rate_limit(
    redis: Redis,
    identifier: str,
    tokens: int,
    period_seconds: int,
) -> None:
    key = rate_limit_key(identifier)
    pipe = redis.pipeline()
    pipe.incr(key, 1)
    pipe.ttl(key)
    current, ttl = await pipe.execute()
    if ttl == -1:
        await redis.expire(key, period_seconds)
    if current > tokens:
        raise RateLimitExceededError(tokens=tokens, period_seconds=period_seconds)


class RateLimitExceededError(Exception):
    def __init__(self, tokens: int, period_seconds: int) -> None:
        self.tokens = tokens
        self.period_seconds = period_seconds
        message = f"Rate limit exceeded ({tokens} per {period_seconds}s)"
        super().__init__(message)


@dataclass(slots=True)
class TimerState:
    timer_id: str
    user_id: str
    label: str
    duration_seconds: int
    end_ts: float

    @property
    def ends_at(self) -> datetime:
        return datetime.fromtimestamp(self.end_ts, tz=timezone.utc)

    def remaining_seconds(self, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        remaining = int(self.end_ts - now.timestamp())
        return remaining if remaining > 0 else 0


def decode_timer_state(
    data: Optional[Dict[str, Any]], timer_id: str
) -> Optional[TimerState]:
    if not data:
        return None
    try:
        end_ts = float(data["end_ts"])
        return TimerState(
            timer_id=timer_id,
            user_id=str(data["user_id"]),
            label=str(data.get("label", "Pomodoro")),
            duration_seconds=int(data.get("duration_sec", 0)),
            end_ts=end_ts,
        )
    except (KeyError, ValueError, TypeError):
        return None
