from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict

import pytest
from freezegun import freeze_time
from httpx import AsyncClient


async def register_and_login(
    client: AsyncClient, email: str, password: str
) -> Dict[str, str]:
    register = await client.post(
        "/auth/register", json={"email": email, "password": password}
    )
    assert register.status_code == 201
    login = await client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_timer_lifecycle_with_etag_and_completion(client: AsyncClient) -> None:
    headers = await register_and_login(client, "timer@example.com", "TimerPass123")

    create = await client.post(
        "/timers",
        json={"duration_seconds": 5, "label": "Focus"},
        headers=headers,
    )
    assert create.status_code == 201
    timer = create.json()
    timer_id = timer["id"]

    tick = await client.get(
        f"/timers/{timer_id}/tick",
        headers=headers,
        params={"wait": "false"},
    )
    assert tick.status_code == 200
    etag = tick.headers["ETag"]
    payload = tick.json()
    assert payload["status"] == "running"
    assert 0 < payload["remaining_seconds"] <= 5

    cached = await client.get(
        f"/timers/{timer_id}/tick",
        headers={**headers, "If-None-Match": etag},
        params={"wait": "false"},
    )
    assert cached.status_code == 304

    ends_at = datetime.fromisoformat(timer["ends_at"].replace("Z", "+00:00"))
    with freeze_time((ends_at + timedelta(seconds=1)).astimezone(timezone.utc)):
        finished = await client.get(
            f"/timers/{timer_id}/tick",
            headers=headers,
            params={"wait": "false"},
        )
    assert finished.status_code == 200
    assert finished.json()["status"] == "completed"
    assert finished.json()["remaining_seconds"] == 0


@pytest.mark.anyio
async def test_cancel_timer(client: AsyncClient) -> None:
    headers = await register_and_login(client, "cancel@example.com", "CancelPass123")
    create = await client.post(
        "/timers",
        json={"duration_seconds": 120, "label": "Cancel"},
        headers=headers,
    )
    timer_id = create.json()["id"]

    cancel = await client.post(f"/timers/{timer_id}/cancel", headers=headers)
    assert cancel.status_code == 200
    body = cancel.json()
    assert body["status"] == "canceled"

    tick = await client.get(
        f"/timers/{timer_id}/tick",
        headers=headers,
        params={"wait": "false"},
    )
    assert tick.status_code == 200
    tick_payload = tick.json()
    assert tick_payload["status"] == "canceled"
    assert tick_payload["remaining_seconds"] == 0


@pytest.mark.anyio
async def test_batch_tick_detects_changes(client: AsyncClient) -> None:
    headers = await register_and_login(client, "batch@example.com", "BatchPass123")
    first = await client.post(
        "/timers", json={"duration_seconds": 300, "label": "One"}, headers=headers
    )
    second = await client.post(
        "/timers", json={"duration_seconds": 300, "label": "Two"}, headers=headers
    )
    timer_ids = [first.json()["id"], second.json()["id"]]

    initial = await client.post(
        "/timers/batch/tick",
        json={"timer_ids": timer_ids, "wait": False},
        headers=headers,
    )
    assert initial.status_code == 200
    payload = initial.json()
    assert len(payload["timers"]) == 2

    etag_map = {item["id"]: item["etag"] for item in payload["timers"]}
    unchanged = await client.post(
        "/timers/batch/tick",
        json={"timer_ids": timer_ids, "wait": False, "client_etags": etag_map},
        headers=headers,
    )
    assert unchanged.status_code == 200
    final_payload = unchanged.json()
    assert final_payload["timers"] == []
    assert sorted(final_payload["not_modified"]) == sorted(timer_ids)


@pytest.mark.anyio
async def test_list_timers_returns_all(client: AsyncClient) -> None:
    headers = await register_and_login(client, "list@example.com", "ListPass123")
    await client.post(
        "/timers", json={"duration_seconds": 60, "label": "A"}, headers=headers
    )
    await client.post(
        "/timers", json={"duration_seconds": 60, "label": "B"}, headers=headers
    )

    listing = await client.get("/timers", headers=headers)
    assert listing.status_code == 200
    timers = listing.json()
    assert len(timers) == 2
    labels = {t["label"] for t in timers}
    assert labels == {"A", "B"}
