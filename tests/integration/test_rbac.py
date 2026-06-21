"""RBAC integration tests — admin-only routes reject lesser roles."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from seedbank.core.security import hash_password
from seedbank.infrastructure.db.enums import UserRole
from seedbank.infrastructure.db.models import User
from seedbank.infrastructure.db.repositories import UserRepository

pytestmark = pytest.mark.integration


async def _seed_user(db_session: AsyncSession, *, email: str, role: UserRole) -> User:
    repo = UserRepository(db_session)
    user = User(
        email=email,
        hashed_password=hash_password("StrongPasswd1A"),
        role=role.value,
        is_active=True,
        is_verified=True,
    )
    await repo.add(user)
    await db_session.commit()
    return user


async def _login(client: AsyncClient, email: str) -> str:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPasswd1A"},
    )
    assert r.status_code == 200, r.text
    token: str = r.json()["data"]["access_token"]
    return token


async def test_end_user_cannot_list_users(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_user(db_session, email="end@e.com", role=UserRole.END_USER)
    token = await _login(app_client, "end@e.com")

    r = await app_client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


async def test_admin_can_list_users(app_client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed_user(db_session, email="admin@e.com", role=UserRole.ADMIN)
    token = await _login(app_client, "admin@e.com")

    r = await app_client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["data"], list)
    assert body["meta"]["total"] >= 1
    assert any(u["email"] == "admin@e.com" for u in body["data"])


async def test_ai_developer_cannot_list_users(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_user(db_session, email="dev@e.com", role=UserRole.AI_DEVELOPER)
    token = await _login(app_client, "dev@e.com")

    r = await app_client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
