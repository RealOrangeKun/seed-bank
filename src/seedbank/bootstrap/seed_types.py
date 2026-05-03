"""Idempotent seed-type catalog bootstrap.

Mirror image of :mod:`seedbank.bootstrap.users`: takes a list of specs,
performs an ``INSERT ... ON CONFLICT DO NOTHING`` keyed on the unique
``seed_types.code``. Re-running never overwrites existing rows — admins
can retune ``default_confidence_threshold`` without fear of being reset.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.dialects.postgresql import insert as pg_insert

from seedbank.core.ids import uuid7
from seedbank.core.logging import get_logger
from seedbank.infrastructure.db.models import SeedType

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SeedTypeSpec:
    code: str
    display_name: str
    default_confidence_threshold: Decimal = Decimal("0.5000")


async def bootstrap_seed_types(
    session: AsyncSession, specs: list[SeedTypeSpec]
) -> int:
    """Upsert the seed-type catalog. Returns rows inserted."""
    if not specs:
        return 0
    rows = [
        {
            "id": uuid7(),
            "code": spec.code,
            "display_name": spec.display_name,
            "default_confidence_threshold": spec.default_confidence_threshold,
        }
        for spec in specs
    ]
    stmt = (
        pg_insert(SeedType)
        .values(rows)
        .on_conflict_do_nothing(index_elements=[SeedType.code])
    )
    result = await session.execute(stmt)
    inserted = result.rowcount or 0
    log.info("bootstrap.seed_types", requested=len(rows), inserted=inserted)
    return inserted
