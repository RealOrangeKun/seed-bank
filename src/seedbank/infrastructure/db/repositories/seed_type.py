"""SeedType repository.

The seed-type catalog is small, curated reference data (coffee, maize,
lentil, ...) seeded via migrations + ``scripts/seed_dev.py``. The API only
reads it, so a single ordered list query is all this repository needs.
"""

from __future__ import annotations

from sqlalchemy import select

from seedbank.infrastructure.db.models import SeedType

from .base import Repository


class SeedTypeRepository(Repository[SeedType]):
    model = SeedType

    async def list_all(self) -> list[SeedType]:
        """Every seed type, ordered by ``display_name`` for stable dropdowns."""
        stmt = select(SeedType).order_by(SeedType.display_name.asc())
        return list((await self.session.execute(stmt)).scalars().all())
