"""Idempotent global-supplier bootstrap.

Mirror image of :mod:`seedbank.bootstrap.seed_types`: takes a list of
specs and performs ``INSERT ... ON CONFLICT DO NOTHING`` keyed on the
unique ``suppliers.slug``. Re-running never overwrites existing rows.

Only *global* suppliers are seeded (``is_global=True``,
``created_by_user_id IS NULL``) — they're the admin-curated catalog every
user sees. Private suppliers are created by users through the API, never
seeded. The slug is deterministic (derived from the name) so re-running
collides on the same row instead of inserting a duplicate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.dialects.postgresql import insert as pg_insert

from seedbank.core.ids import uuid7
from seedbank.core.logging import get_logger
from seedbank.infrastructure.db.models import Supplier

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

log = get_logger(__name__)

_SLUG_SUB = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    return _SLUG_SUB.sub("-", name.strip().lower()).strip("-") or "supplier"


@dataclass(frozen=True, slots=True)
class GlobalSupplierSpec:
    name: str


async def bootstrap_suppliers(session: AsyncSession, specs: list[GlobalSupplierSpec]) -> int:
    """Upsert the global supplier catalog. Returns rows inserted."""
    if not specs:
        return 0
    rows = [
        {
            "id": uuid7(),
            "name": spec.name,
            "slug": _slugify(spec.name),
            "is_global": True,
            "created_by_user_id": None,
            "is_active": True,
        }
        for spec in specs
    ]
    stmt = pg_insert(Supplier).values(rows).on_conflict_do_nothing(index_elements=[Supplier.slug])
    result = await session.execute(stmt)
    inserted = result.rowcount or 0  # type: ignore[attr-defined]
    log.info("bootstrap.suppliers", requested=len(rows), inserted=inserted)
    return inserted
