"""Integration tests for API-key issuance + use as `X-API-Key`."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from seedbank.core.security import hash_password
from seedbank.infrastructure.db.enums import UserRole
from seedbank.infrastructure.db.models import User
from seedbank.infrastructure.db.repositories import UserRepository

pytestmark = pytest.mark.integration


async def _seed_and_login(client: AsyncClient, db_session: AsyncSession, email: str) -> str:
    repo = UserRepository(db_session)
    user = User(
        email=email,
        hashed_password=hash_password("StrongPasswd1A"),
        role=UserRole.END_USER.value,
        is_active=True,
        is_verified=True,
    )
    await repo.add(user)
    await db_session.commit()

    r = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPasswd1A"},
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]["access_token"]


async def test_create_use_revoke_api_key(app_client: AsyncClient, db_session: AsyncSession) -> None:
    bearer = await _seed_and_login(app_client, db_session, "k@e.com")

    # Create
    r = await app_client.post(
        "/api/v1/api-keys",
        headers={"Authorization": f"Bearer {bearer}"},
        json={"name": "Laptop", "scopes": ["analyze:write"]},
    )
    assert r.status_code == 201, r.text
    body = r.json()["data"]
    plaintext = body["key"]
    key_id = body["id"]
    assert plaintext.startswith("seedbank_")
    assert body["prefix"]
    assert len(body["prefix"]) == 8

    # /me via X-API-Key
    r = await app_client.get("/api/v1/users/me", headers={"X-API-Key": plaintext})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["email"] == "k@e.com"

    # Subsequent list does NOT expose the plaintext (the schema field defaults
    # to None and we only set it on creation).
    r = await app_client.get("/api/v1/api-keys", headers={"Authorization": f"Bearer {bearer}"})
    assert r.status_code == 200
    body = r.json()
    rows = body["data"]
    assert body["meta"]["total"] >= 1
    assert any(row["id"] == key_id and row.get("key") is None for row in rows)

    # Revoke
    r = await app_client.delete(
        f"/api/v1/api-keys/{key_id}",
        headers={"Authorization": f"Bearer {bearer}"},
    )
    assert r.status_code == 204

    # Reuse after revoke fails
    r = await app_client.get("/api/v1/users/me", headers={"X-API-Key": plaintext})
    assert r.status_code == 401


async def test_invalid_api_key_rejected(app_client: AsyncClient) -> None:
    r = await app_client.get(
        "/api/v1/users/me", headers={"X-API-Key": "seedbank_obviouslyfake1234"}
    )
    assert r.status_code == 401
