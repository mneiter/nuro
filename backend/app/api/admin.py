from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Timer, TimerStatus
from ..schemas.timer import TimerSummary

from .deps import get_current_admin

router = APIRouter(dependencies=[Depends(get_current_admin)])


@router.get("/timers/summary", response_model=TimerSummary)
async def timers_summary(
    session: AsyncSession = Depends(get_session),
) -> TimerSummary:
    status_counts = {
        TimerStatus.RUNNING: 0,
        TimerStatus.COMPLETED: 0,
        TimerStatus.CANCELED: 0,
    }

    result = await session.execute(
        select(Timer.status, func.count(Timer.id)).group_by(Timer.status)
    )
    for status, count in result:
        status_counts[status] = count

    total = sum(status_counts.values())
    active_users_result = await session.execute(
        select(func.count(func.distinct(Timer.user_id)))
    )
    active_users = active_users_result.scalar_one()

    return TimerSummary(
        total=total,
        running=status_counts[TimerStatus.RUNNING],
        completed=status_counts[TimerStatus.COMPLETED],
        canceled=status_counts[TimerStatus.CANCELED],
        active_users=active_users,
    )
