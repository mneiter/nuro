from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


class TimerStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELED = "canceled"


class Timer(Base):
    __tablename__ = "timers"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(128), nullable=False, default="Pomodoro")
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[TimerStatus] = mapped_column(
        SAEnum(TimerStatus, name="timerstatus"),
        default=TimerStatus.RUNNING,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    canceled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="timers")

    def touch(self) -> None:
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)

    def mark_completed(self, when: Optional[datetime] = None) -> None:
        completion_time = when or datetime.now(timezone.utc)
        self.status = TimerStatus.COMPLETED
        self.completed_at = completion_time
        self.ends_at = completion_time
        self.touch()

    def mark_canceled(self, when: Optional[datetime] = None) -> None:
        cancel_time = when or datetime.now(timezone.utc)
        self.status = TimerStatus.CANCELED
        self.canceled_at = cancel_time
        self.touch()
