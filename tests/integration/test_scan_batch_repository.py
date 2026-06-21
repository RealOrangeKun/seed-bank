"""Integration tests for :class:`ScanBatchRepository.list_for_user_with_counts`.

Runs against a real Postgres testcontainer (no mocks at this boundary).
Pins the bug fix for ``GET /batches`` returning ``image_count=0``: the
list page must carry each batch's real image count, derived in one grouped
query (LEFT JOIN so a batch with zero images stays in the page at count 0).
Ownership scoping and ``submitted_at desc`` ordering match
``list_for_user``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from seedbank.infrastructure.db.enums import UserRole
from seedbank.infrastructure.db.models import ScanBatch, ScanImage, User
from seedbank.infrastructure.db.repositories import ScanBatchRepository

pytestmark = pytest.mark.integration


async def _seed_user(db_session: AsyncSession, email: str) -> User:
    user = User(
        email=email,
        hashed_password="bcrypt$irrelevant",
        role=UserRole.END_USER.value,
    )
    db_session.add(user)
    await db_session.flush()
    return user


def _batch(user_id, *, submitted_at: datetime) -> ScanBatch:
    return ScanBatch(
        user_id=user_id,
        status="pending",
        source="api",
        submitted_at=submitted_at,
    )


def _image(batch_id, key: str) -> ScanImage:
    return ScanImage(
        batch_id=batch_id,
        storage_key=key,
        content_type="image/png",
        size_bytes=123,
        sha256="0" * 64,
    )


async def test_counts_match_image_rows_and_zero_when_empty(
    db_session: AsyncSession,
) -> None:
    user = await _seed_user(db_session, "counts@example.com")
    now = datetime.now(UTC)
    two_images = _batch(user.id, submitted_at=now)
    empty = _batch(user.id, submitted_at=now - timedelta(seconds=5))
    db_session.add_all([two_images, empty])
    await db_session.flush()
    db_session.add_all(
        [
            _image(two_images.id, "a.png"),
            _image(two_images.id, "b.png"),
        ]
    )
    await db_session.commit()

    repo = ScanBatchRepository(db_session)
    rows = await repo.list_for_user_with_counts(user.id, limit=50, offset=0)

    counts = {batch.id: count for batch, count in rows}
    assert counts[two_images.id] == 2
    assert counts[empty.id] == 0  # LEFT JOIN keeps the empty batch


async def test_counts_respect_ownership_and_ordering(
    db_session: AsyncSession,
) -> None:
    alice = await _seed_user(db_session, "alice-batch@example.com")
    bob = await _seed_user(db_session, "bob-batch@example.com")
    base = datetime.now(UTC)
    newer = _batch(alice.id, submitted_at=base + timedelta(seconds=10))
    older = _batch(alice.id, submitted_at=base)
    bob_batch = _batch(bob.id, submitted_at=base)
    db_session.add_all([newer, older, bob_batch])
    await db_session.flush()
    db_session.add_all([_image(newer.id, "n.png"), _image(bob_batch.id, "x.png")])
    await db_session.commit()

    repo = ScanBatchRepository(db_session)
    rows = await repo.list_for_user_with_counts(alice.id, limit=50, offset=0)

    # Only Alice's batches, newest first.
    assert [batch.id for batch, _ in rows] == [newer.id, older.id]
    counts = {batch.id: count for batch, count in rows}
    assert counts[newer.id] == 1
    assert counts[older.id] == 0
