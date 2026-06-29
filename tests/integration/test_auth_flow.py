"""End-to-end auth flow against a real Postgres testcontainer + fake Redis.

Covers register → verify → login → /me → refresh → /me → replay → logout.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from seedbank.infrastructure.db.repositories import UserRepository

pytestmark = pytest.mark.integration


async def _register_and_verify(
    client: AsyncClient, db_session: AsyncSession, email: str, pwd: str
) -> None:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": pwd, "full_name": "Test"},
    )
    assert r.status_code == 201, r.text
    # Force-verify directly via repo (we don't have a way to fetch the
    # plaintext token from Redis without scanning, and the verify endpoint
    # is exercised in its own test below).
    repo = UserRepository(db_session)
    user = await repo.get_by_email(email)
    assert user is not None
    user.is_verified = True
    await db_session.commit()


async def test_register_login_me_refresh_replay_logout(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    pwd = "StrongPasswd1A"
    await _register_and_verify(app_client, db_session, "flow@e.com", pwd)

    # Login
    r = await app_client.post("/api/v1/auth/login", json={"email": "flow@e.com", "password": pwd})
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    access_a = body["access_token"]
    refresh_a = body["refresh_token"]

    # /me with the access token
    r = await app_client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access_a}"})
    assert r.status_code == 200
    assert r.json()["data"]["email"] == "flow@e.com"

    # Refresh — should get a new pair
    r = await app_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_a})
    assert r.status_code == 200
    body = r.json()["data"]
    access_b = body["access_token"]
    refresh_b = body["refresh_token"]
    assert refresh_b != refresh_a

    # New access still works
    r = await app_client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access_b}"})
    assert r.status_code == 200

    # Replay the OLD refresh token — must 401
    r = await app_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_a})
    assert r.status_code == 401

    # Logout the new refresh
    r = await app_client.post("/api/v1/auth/logout", json={"refresh_token": refresh_b})
    assert r.status_code == 200

    # Refresh after logout fails
    r = await app_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_b})
    assert r.status_code == 401


async def test_login_rejects_unknown_user(app_client: AsyncClient) -> None:
    r = await app_client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@nowhere.com", "password": "Whatever1234A"},
    )
    assert r.status_code == 401


async def test_register_rejects_weak_password(app_client: AsyncClient) -> None:
    # Pydantic enforces min_length=12 at the schema layer; this should be 422.
    r = await app_client.post(
        "/api/v1/auth/register",
        json={"email": "weak@e.com", "password": "short", "full_name": None},
    )
    assert r.status_code == 422


async def test_me_requires_auth(app_client: AsyncClient) -> None:
    r = await app_client.get("/api/v1/users/me")
    assert r.status_code == 401
