import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_register_and_login_flow(client: AsyncClient) -> None:
    email = "alice@example.com"
    password = "StrongPass123"

    register = await client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert register.status_code == 201
    register_token = register.json()["access_token"]
    assert register_token

    login = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    assert token

    profile = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile.status_code == 200
    payload = profile.json()
    assert payload["email"] == email


@pytest.mark.anyio
async def test_register_duplicate_email_rejected(client: AsyncClient) -> None:
    email = "dup@example.com"
    password = "Password123"

    first = await client.post(
        "/auth/register", json={"email": email, "password": password}
    )
    assert first.status_code == 201

    second = await client.post(
        "/auth/register", json={"email": email, "password": password}
    )
    assert second.status_code == 409
    assert "Email" in second.json()["detail"]
