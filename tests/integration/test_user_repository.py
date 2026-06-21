"""Integration tests for the User repository against a real Postgres."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from seedbank.infrastructure.db.enums import UserRole
from seedbank.infrastructure.db.models import User
from seedbank.infrastructure.db.repositories import UserRepository

pytestmark = pytest.mark.integration


async def test_get_by_email_roundtrip(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    user = User(
        email="alice@example.com",
        hashed_password="bcrypt$irrelevant",
        full_name="Alice",
        role=UserRole.END_USER.value,
        is_active=True,
        is_verified=True,
    )
    await repo.add(user)
    await db_session.commit()

    fetched = await repo.get_by_email("alice@example.com")
    assert fetched is not None
    assert fetched.id == user.id

    # Email is citext — uppercase lookup must match.
    fetched_upper = await repo.get_by_email("ALICE@example.com")
    assert fetched_upper is not None and fetched_upper.id == user.id


async def test_soft_deleted_user_is_invisible(db_session: AsyncSession) -> None:
    from datetime import datetime, timezone

    repo = UserRepository(db_session)
    user = User(
        email="bob@example.com",
        hashed_password="bcrypt$irrelevant",
        role=UserRole.END_USER.value,
        deleted_at=datetime.now(tz=timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()

    assert await repo.get_by_email("bob@example.com") is None
    assert await repo.get_by_id_active(user.id) is None
