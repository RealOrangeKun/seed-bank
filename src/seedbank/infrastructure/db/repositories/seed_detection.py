"""SeedDetection repository — bulk-friendly writes.

The detect stage produces N detection rows per image; the classify stage
later updates the ``quality`` column on each. Both paths are bulk-shaped
to keep the worker's per-image round-trip count flat.

Confidence is ``NUMERIC(5,4)`` and bbox columns are ``NUMERIC(7,6)`` —
the caller passes ``Decimal`` values directly. No float coercion here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import update

from seedbank.core.logging import get_logger
from seedbank.infrastructure.db.models import SeedDetection

from .base import Repository

if TYPE_CHECKING:
    from uuid import UUID

log = get_logger(__name__)


class SeedDetectionRepository(Repository[SeedDetection]):
    model = SeedDetection

    async def add_many(self, rows: list[SeedDetection]) -> None:
        """Insert a batch of pre-built detection rows in one round trip."""
        if not rows:
            return
        self.session.add_all(rows)
        await self.session.flush()
        log.info("seed_detection.add_many", count=len(rows))

    async def update_quality_many(self, updates: list[tuple[UUID, str]]) -> int:
        """Set ``quality`` on each ``(detection_id, quality)`` pair.

        Issues one statement per pair — small N (one per crop) makes a CASE
        expression more code than it's worth. Returns total rows affected.
        """
        if not updates:
            return 0
        total = 0
        for detection_id, quality in updates:
            stmt = (
                update(SeedDetection)
                .where(SeedDetection.id == detection_id)
                .values(quality=quality)
                # See ``ScanBatchRepository.cas_status``: bulk UPDATE +
                # AsyncSession identity-map sync risks ``MissingGreenlet``
                # on later attribute reads. Callers in ``analyze.py`` do not
                # read mutated attrs back, but be explicit anyway.
                .execution_options(synchronize_session=False)
            )
            result = await self.session.execute(stmt)
            total += result.rowcount or 0
        log.info(
            "seed_detection.update_quality_many",
            requested=len(updates),
            updated=total,
        )
        return total
