"""Integration tests for :class:`SeedTypeRepository.list_all`.

Runs against a real Postgres testcontainer (no mocks at this boundary).
Pins the contract the catalog dropdown depends on: every seed type is
returned, ordered by ``display_name``.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from seedbank.infrastructure.db.models import SeedType
from seedbank.infrastructure.db.repositories import SeedTypeRepository

pytestmark = pytest.mark.integration


async def test_list_all_returns_every_seed_type_ordered_by_display_name(
    db_session: AsyncSession,
) -> None:
    db_session.add_all(
        [
            SeedType(code="maize", display_name="Maize"),
            SeedType(code="coffee", display_name="Coffee"),
            SeedType(
                code="lentil",
                display_name="Lentil",
                default_confidence_threshold=Decimal("0.6000"),
            ),
        ]
    )
    await db_session.commit()

    repo = SeedTypeRepository(db_session)
    rows = await repo.list_all()

    assert [r.display_name for r in rows] == ["Coffee", "Lentil", "Maize"]
    lentil = next(r for r in rows if r.code == "lentil")
    assert lentil.default_confidence_threshold == Decimal("0.6000")


async def test_list_all_empty_catalog_returns_empty(
    db_session: AsyncSession,
) -> None:
    repo = SeedTypeRepository(db_session)
    assert await repo.list_all() == []
