from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from ..models.timer import TimerStatus


class TimerBase(BaseModel):
    label: str = Field(default="Pomodoro", max_length=128)


class TimerCreate(TimerBase):
    duration_seconds: int = Field(
        default=1500, ge=60, le=60 * 60 * 8
    )  # 1 min - 8 hours


class TimerOut(BaseModel):
    id: str
    label: str
    duration_seconds: int
    status: TimerStatus
    started_at: datetime
    ends_at: datetime
    completed_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    remaining_seconds: int
    etag: str
    last_modified: datetime

    model_config = {"from_attributes": True}


class TimerTickResponse(BaseModel):
    id: str
    status: TimerStatus
    label: str
    ends_at: datetime
    remaining_seconds: int
    etag: str
    last_modified: datetime

    model_config = {"from_attributes": True}


class TimerBatchTickItem(TimerTickResponse):
    pass


class TimerBatchTickRequest(BaseModel):
    timer_ids: List[str]
    wait: bool = True
    client_etags: Optional[Dict[str, str]] = None
    timeout_seconds: Optional[float] = None

    @field_validator("timer_ids")
    @classmethod
    def ensure_unique_ids(cls, value: List[str]) -> List[str]:
        if len(value) != len(set(value)):
            raise ValueError("timer_ids must be unique")
        return value


class TimerBatchTickResponse(BaseModel):
    timers: List[TimerBatchTickItem]
    not_modified: List[str] = Field(default_factory=list)


class TimerSummary(BaseModel):
    total: int
    running: int
    completed: int
    canceled: int
    active_users: int
