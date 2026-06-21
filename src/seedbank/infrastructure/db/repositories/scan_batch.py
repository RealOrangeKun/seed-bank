"""ScanBatch repository — batches, their images, and the inferences/detections
joined under each."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import desc, func, select, update
from sqlalchemy.orm import selectinload

from seedbank.core.logging import get_logger
from seedbank.infrastructure.db.models import (
    Inference,
    ScanBatch,
    ScanImage,
    SeedDetection,
)

from .base import Repository

if TYPE_CHECKING:
    from uuid import UUID

    from seedbank.infrastructure.db.enums import BatchStatus

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class CasResult:
    """Result of a compare-and-set status flip.

    ``won`` is true iff this caller flipped the row. ``started_at`` and
    ``finished_at`` carry the canonical DB-side timestamps that were just
    set by the UPDATE — populated by ``RETURNING``, so callers don't have
    to re-fetch or fall back to a local Python clock.
    """

    won: bool
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ScanBatchRepository(Repository[ScanBatch]):
    model = ScanBatch

    async def get_for_user(self, batch_id: UUID, user_id: UUID) -> ScanBatch | None:
        """Fetch a batch the caller owns. Soft-deleted rows excluded."""
        stmt = select(ScanBatch).where(
            ScanBatch.id == batch_id,
            ScanBatch.user_id == user_id,
            ScanBatch.deleted_at.is_(None),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
        supplier_id: UUID | None = None,
        country_code: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[ScanBatch]:
        stmt = select(ScanBatch).where(
            ScanBatch.user_id == user_id,
            ScanBatch.deleted_at.is_(None),
        )
        if supplier_id is not None:
            stmt = stmt.where(ScanBatch.supplier_id == supplier_id)
        if country_code is not None:
            stmt = stmt.where(ScanBatch.geo_country_code == country_code)
        if since is not None:
            stmt = stmt.where(ScanBatch.submitted_at >= since)
        if until is not None:
            stmt = stmt.where(ScanBatch.submitted_at <= until)

        stmt = stmt.order_by(desc(ScanBatch.submitted_at)).limit(limit).offset(offset)
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_for_user(
        self,
        user_id: UUID,
        *,
        supplier_id: UUID | None = None,
        country_code: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> int:
        """Total batches the user owns, filtered the same way as
        :meth:`list_for_user`. Used to populate the ``Page.meta.total``."""
        stmt = (
            select(func.count())
            .select_from(ScanBatch)
            .where(
                ScanBatch.user_id == user_id,
                ScanBatch.deleted_at.is_(None),
            )
        )
        if supplier_id is not None:
            stmt = stmt.where(ScanBatch.supplier_id == supplier_id)
        if country_code is not None:
            stmt = stmt.where(ScanBatch.geo_country_code == country_code)
        if since is not None:
            stmt = stmt.where(ScanBatch.submitted_at >= since)
        if until is not None:
            stmt = stmt.where(ScanBatch.submitted_at <= until)
        return int((await self.session.execute(stmt)).scalar_one())

    async def get_with_images_and_detections(
        self, batch_id: UUID, user_id: UUID
    ) -> ScanBatch | None:
        """Eager-load images → inferences → detections for the batch detail
        view. Uses `selectinload` so each level is one extra query, not an N+1."""
        stmt = (
            select(ScanBatch)
            .where(
                ScanBatch.id == batch_id,
                ScanBatch.user_id == user_id,
                ScanBatch.deleted_at.is_(None),
            )
            .options(
                selectinload(ScanBatch.images)
                .selectinload(ScanImage.inferences)
                .selectinload(Inference.detections)
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_with_full_graph(self, batch_id: UUID) -> ScanBatch | None:
        """Same as ``get_with_images_and_detections`` but without the
        ``user_id`` filter. Caller (admin paths, worker) is responsible for
        ownership checks. Soft-deleted rows are still excluded."""
        stmt = (
            select(ScanBatch)
            .where(
                ScanBatch.id == batch_id,
                ScanBatch.deleted_at.is_(None),
            )
            .options(
                selectinload(ScanBatch.images)
                .selectinload(ScanImage.inferences)
                .selectinload(Inference.detections)
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def cas_status(
        self,
        batch_id: UUID,
        *,
        expected: BatchStatus,
        new: BatchStatus,
        set_started_at: bool = False,
        set_finished_at: bool = False,
    ) -> CasResult:
        """Compare-and-set ``status`` from ``expected`` to ``new``.

        Returns a :class:`CasResult`. ``won`` is true iff exactly one row was
        updated; concurrent workers racing on the same batch get
        ``won=False`` and treat that as "not first, no-op". When the caller
        asks for ``set_started_at`` / ``set_finished_at``, the DB-side
        ``func.now()`` value is returned via ``RETURNING`` so the caller has
        the canonical timestamp without re-fetching.
        """
        values: dict[str, object] = {"status": new.value}
        if set_started_at:
            values["started_at"] = func.now()
        if set_finished_at:
            values["finished_at"] = func.now()

        stmt = (
            update(ScanBatch)
            .where(
                ScanBatch.id == batch_id,
                ScanBatch.status == expected.value,
            )
            .values(**values)
            .returning(ScanBatch.started_at, ScanBatch.finished_at)
            # ``synchronize_session=False`` avoids SA's identity-map sync.
            # Combined with ``RETURNING``, the caller gets the post-update
            # values directly and never reads stale columns off the in-memory
            # ORM object.
            .execution_options(synchronize_session=False)
        )
        row = (await self.session.execute(stmt)).first()
        log.info(
            "scan_batch.cas_status",
            batch_id=str(batch_id),
            **{"from": expected.value, "to": new.value},
            won=row is not None,
        )
        if row is None:
            return CasResult(won=False)
        return CasResult(won=True, started_at=row[0], finished_at=row[1])

    async def list_detections_for_batch(self, batch_id: UUID, user_id: UUID) -> list[SeedDetection]:
        """Flat list of every detection across the batch's images + models."""
        stmt = (
            select(SeedDetection)
            .join(Inference, SeedDetection.inference_id == Inference.id)
            .join(ScanImage, Inference.image_id == ScanImage.id)
            .join(ScanBatch, ScanImage.batch_id == ScanBatch.id)
            .where(
                ScanBatch.id == batch_id,
                ScanBatch.user_id == user_id,
                ScanBatch.deleted_at.is_(None),
            )
        )
        return list((await self.session.execute(stmt)).scalars().all())
