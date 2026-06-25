"""SeedType repository.

The seed-type catalog is small, curated reference data (coffee, maize,
lentil, ...) seeded via migrations + ``scripts/seed_dev.py``. The API only
reads it, so a single ordered list query is all this repository needs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from seedbank.infrastructure.db.models import SeedType

from .base import Repository

if TYPE_CHECKING:
    from uuid import UUID


class SeedTypeRepository(Repository[SeedType]):
    model = SeedType

    async def list_all(self) -> list[SeedType]:
        """Every seed type, ordered by ``display_name`` for stable dropdowns."""
        stmt = select(SeedType).order_by(SeedType.display_name.asc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def code_to_id(self) -> dict[str, UUID]:
        """Map ``code`` → ``id`` for the whole (small) catalog.

        The detector returns class names like ``"coffee"``/``"maize"``; the
        analyze worker uses this to stamp each detection with its seed-type id
        so per-type quality classifiers can be routed. Catalog is tiny, so one
        query is cheap and avoids an N+1 per detection.
        """
        rows = await self.list_all()
        return {row.code: row.id for row in rows}
