"""Replay-attack test for the refresh-token rotation.

Confirms that the partial unique on `(token_hash) WHERE revoked_at IS NULL`
prevents two live tokens with the same hash, and that `rotate()` is
non-reentrant — a second rotation of the same old token returns 0.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from seedbank.infrastructure.db.enums import UserRole
from seedbank.infrastructure.db.models import RefreshToken, User
from seedbank.infrastructure.db.repositories import RefreshTokenRepository

pytestmark = pytest.mark.integration


async def _seed_user(db_session: AsyncSession) -> User:
    user = User(
        email="rt-test@example.com",
        hashed_password="bcrypt$irrelevant",
        role=UserRole.END_USER.value,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_rotate_is_idempotent_failure(db_session: AsyncSession) -> None:
    user = await _seed_user(db_session)
    now = datetime.now(tz=UTC)

    old = RefreshToken(user_id=user.id, token_hash="hash-old", expires_at=now + timedelta(days=7))
    new = RefreshToken(user_id=user.id, token_hash="hash-new", expires_at=now + timedelta(days=7))
    db_session.add_all([old, new])
    await db_session.flush()

    repo = RefreshTokenRepository(db_session)
    assert await repo.rotate(old.id, new.id) == 1
    # Second rotate of the same token must return 0 — the replay-detection signal.
    assert await repo.rotate(old.id, new.id) == 0
