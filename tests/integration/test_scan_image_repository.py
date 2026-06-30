"""Integration tests for ``ScanImageRepository.list_for_batch``.

Runs against a real Postgres testcontainer (no mocks at this boundary).
Pins the contract the batch image-urls path depends on: every image in a
batch is returned, ordered by ``uploaded_at`` then ``id`` (stable across
ties), and an unknown batch yields an empty list rather than an error.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from seedbank.infrastructure.db.enums import UserRole
from seedbank.infrastructure.db.models import ScanBatch, ScanImage, User
from seedbank.infrastructure.db.repositories import ScanImageRepository

pytestmark = pytest.mark.integration


async def _seed_batch(db_session: AsyncSession) -> ScanBatch:
    user = User(
        email="scan-img@example.com",
        hashed_password="bcrypt$irrelevant",
        role=UserRole.END_USER.value,
    )
    db_session.add(user)
    await db_session.flush()

    batch = ScanBatch(user_id=user.id, status="pending", source="api")
    db_session.add(batch)
    await db_session.flush()
    return batch


def _image(batch_id: UUID, *, key: str, uploaded_at: datetime) -> ScanImage:
    return ScanImage(
        batch_id=batch_id,
        storage_key=key,
        content_type="image/png",
        size_bytes=123,
        sha256="0" * 64,
        uploaded_at=uploaded_at,
    )


async def test_list_for_batch_returns_all_images_for_the_batch(
    db_session: AsyncSession,
) -> None:
    batch = await _seed_batch(db_session)
    now = datetime.now(UTC)
    db_session.add_all(
        [
            _image(batch.id, key="img/1.png", uploaded_at=now),
            _image(batch.id, key="img/2.png", uploaded_at=now + timedelta(seconds=1)),
            _image(batch.id, key="img/3.png", uploaded_at=now + timedelta(seconds=2)),
        ]
    )
    await db_session.commit()

    repo = ScanImageRepository(db_session)
    rows = await repo.list_for_batch(batch.id)

    assert {r.storage_key for r in rows} == {"img/1.png", "img/2.png", "img/3.png"}


async def test_list_for_batch_orders_by_uploaded_at_then_id(
    db_session: AsyncSession,
) -> None:
    batch = await _seed_batch(db_session)
    base = datetime.now(UTC)
    # Insert out of upload order; the query must sort, not rely on PK order.
    db_session.add_all(
        [
            _image(batch.id, key="late.png", uploaded_at=base + timedelta(seconds=10)),
            _image(batch.id, key="early.png", uploaded_at=base),
            _image(batch.id, key="mid.png", uploaded_at=base + timedelta(seconds=5)),
        ]
    )
    await db_session.commit()

    repo = ScanImageRepository(db_session)
    rows = await repo.list_for_batch(batch.id)

    assert [r.storage_key for r in rows] == ["early.png", "mid.png", "late.png"]


async def test_list_for_batch_breaks_uploaded_at_ties_by_id(
    db_session: AsyncSession,
) -> None:
    """When ``uploaded_at`` is identical the order falls back to ``id``;
    UUIDv7 PKs are time-sortable, so insertion order is the tie-break."""
    batch = await _seed_batch(db_session)
    same = datetime.now(UTC)
    first = _image(batch.id, key="first.png", uploaded_at=same)
    second = _image(batch.id, key="second.png", uploaded_at=same)
    db_session.add_all([first, second])
    await db_session.commit()

    repo = ScanImageRepository(db_session)
    rows = await repo.list_for_batch(batch.id)

    by_id = sorted([first, second], key=lambda i: i.id)
    assert [r.id for r in rows] == [i.id for i in by_id]


async def test_list_for_batch_unknown_batch_returns_empty(
    db_session: AsyncSession,
) -> None:
    from uuid import uuid4

    repo = ScanImageRepository(db_session)
    rows = await repo.list_for_batch(uuid4())

    assert rows == []


async def test_list_for_batch_excludes_images_from_other_batches(
    db_session: AsyncSession,
) -> None:
    batch_a = await _seed_batch(db_session)
    # Second batch under a distinct user to avoid the batch unique surface.
    other_user = User(
        email="scan-img-other@example.com",
        hashed_password="bcrypt$irrelevant",
        role=UserRole.END_USER.value,
    )
    db_session.add(other_user)
    await db_session.flush()
    batch_b = ScanBatch(user_id=other_user.id, status="pending", source="api")
    db_session.add(batch_b)
    await db_session.flush()

    now = datetime.now(UTC)
    db_session.add_all(
        [
            _image(batch_a.id, key="a.png", uploaded_at=now),
            _image(batch_b.id, key="b.png", uploaded_at=now),
        ]
    )
    await db_session.commit()

    repo = ScanImageRepository(db_session)
    rows = await repo.list_for_batch(batch_a.id)

    assert [r.storage_key for r in rows] == ["a.png"]
