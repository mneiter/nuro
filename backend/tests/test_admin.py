from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from freezegun import freeze_time
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import User

from .test_timers import register_and_login


@pytest.mark.anyio
async def test_admin_summary_counts(  # noqa: PLR0915 - readability for test steps
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    admin_headers = await register_and_login(
        client, "admin@example.com", "AdminPass123"
    )
    admin_profile = await client.get("/auth/me", headers=admin_headers)
    admin_id = admin_profile.json()["id"]

    async with session_factory() as session:
        admin_user = await session.get(User, admin_id)
        assert admin_user is not None
        admin_user.is_admin = True
        await session.commit()

    user_headers = await register_and_login(client, "member@example.com", "UserPass123")

    admin_timer_running = await client.post(
        "/timers",
        json={"duration_seconds": 300, "label": "Admin Run"},
        headers=admin_headers,
    )
    assert admin_timer_running.status_code == 201
    running_id = admin_timer_running.json()["id"]

    admin_timer_complete = await client.post(
        "/timers",
        json={"duration_seconds": 120, "label": "Admin Done"},
        headers=admin_headers,
    )
    completed_id = admin_timer_complete.json()["id"]
    ends_at = datetime.fromisoformat(
        admin_timer_complete.json()["ends_at"].replace("Z", "+00:00")
    )
    with freeze_time((ends_at + timedelta(seconds=1)).astimezone(timezone.utc)):
        await client.get(
            f"/timers/{completed_id}/tick",
            headers=admin_headers,
            params={"wait": "false"},
        )

    admin_timer_cancel = await client.post(
        "/timers",
        json={"duration_seconds": 600, "label": "Admin Cancel"},
        headers=admin_headers,
    )
    cancel_id = admin_timer_cancel.json()["id"]
    await client.post(f"/timers/{cancel_id}/cancel", headers=admin_headers)

    await client.post(
        "/timers",
        json={"duration_seconds": 900, "label": "User Run"},
        headers=user_headers,
    )

    summary = await client.get("/admin/timers/summary", headers=admin_headers)
    assert summary.status_code == 200
    payload = summary.json()
    assert payload == {
        "total": 4,
        "running": 2,  # admin running + user running
        "completed": 1,
        "canceled": 1,
        "active_users": 2,
    }

    running_tick = await client.get(
        f"/timers/{running_id}/tick",
        headers=admin_headers,
        params={"wait": "false"},
    )
    assert running_tick.status_code == 200
    assert running_tick.json()["status"] == "running"
