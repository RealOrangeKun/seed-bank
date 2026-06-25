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

    async def list_for_user_with_counts(
        self,
        user_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
        supplier_id: UUID | None = None,
        country_code: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[tuple[ScanBatch, int]]:
        """Same page + filters as :meth:`list_for_user`, but each batch is
        paired with its image count.

        The count comes from a single LEFT JOIN + GROUP BY so the page costs
        one query regardless of size — no N+1, and no denormalized column on
        ``scan_batches`` (CLAUDE.md forbids both). ``LEFT`` keeps batches with
        zero images; ``COUNT(scan_images.id)`` yields 0 for them rather than
        dropping the row.
        """
        count_col = func.count(ScanImage.id)
        stmt = (
            select(ScanBatch, count_col)
            .outerjoin(ScanImage, ScanImage.batch_id == ScanBatch.id)
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

        stmt = (
            stmt.group_by(ScanBatch.id)
            .order_by(desc(ScanBatch.submitted_at))
            .limit(limit)
            .offset(offset)
        )
        rows = (await self.session.execute(stmt)).all()
        return [(batch, int(count)) for batch, count in rows]

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
        """Flat list of every detection across the batch's images + models.

        Ordered by image then detection id so export output is stable across
        repeated calls (CSV diffs stay clean). Soft-deleted batches yield no
        rows — the ownership + ``deleted_at`` filter doubles as the access
        check for the export endpoints.
        """
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
            .order_by(ScanImage.id, SeedDetection.id)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def soft_delete_for_user(self, batch_id: UUID, user_id: UUID) -> bool:
        """Soft-delete one batch the caller owns. Returns ``True`` iff a live
        row was flipped.

        Hard delete is forbidden on soft-delete tables (see ``SoftDeleteMixin``):
        we stamp ``deleted_at`` instead, so the row drops out of every default
        read (all of which filter ``deleted_at IS NULL``). The ``WHERE`` already
        requires ownership and a still-live row, so a second delete — or a
        cross-user attempt — affects zero rows and returns ``False``.
        """
        stmt = (
            update(ScanBatch)
            .where(
                ScanBatch.id == batch_id,
                ScanBatch.user_id == user_id,
                ScanBatch.deleted_at.is_(None),
            )
            .values(deleted_at=func.now())
            .execution_options(synchronize_session=False)
        )
        result = await self.session.execute(stmt)
        won = (result.rowcount or 0) > 0
        log.info("scan_batch.soft_delete", batch_id=str(batch_id), deleted=won)
        return won

    async def soft_delete_many_for_user(self, batch_ids: list[UUID], user_id: UUID) -> int:
        """Soft-delete every owned, still-live batch in ``batch_ids`` in one
        statement. Returns how many rows were actually flipped.

        IDs the caller doesn't own, already-deleted ones, and unknown ones are
        silently skipped by the ``WHERE`` — the count tells the caller how many
        of the requested IDs took effect without leaking which ones existed.
        """
        if not batch_ids:
            return 0
        stmt = (
            update(ScanBatch)
            .where(
                ScanBatch.id.in_(batch_ids),
                ScanBatch.user_id == user_id,
                ScanBatch.deleted_at.is_(None),
            )
            .values(deleted_at=func.now())
            .execution_options(synchronize_session=False)
        )
        result = await self.session.execute(stmt)
        deleted = result.rowcount or 0
        log.info(
            "scan_batch.soft_delete_many",
            requested=len(batch_ids),
            deleted=deleted,
        )
        return deleted

    async def soft_delete_many_any_owner(self, batch_ids: list[UUID]) -> int:
        """Admin-only bulk soft-delete across owners. Returns rows flipped.

        Identical to :meth:`soft_delete_many_for_user` minus the ``user_id``
        filter — callers are responsible for the admin authorization check.
        Already-deleted and unknown IDs are still skipped by the ``WHERE``.
        """
        if not batch_ids:
            return 0
        stmt = (
            update(ScanBatch)
            .where(
                ScanBatch.id.in_(batch_ids),
                ScanBatch.deleted_at.is_(None),
            )
            .values(deleted_at=func.now())
            .execution_options(synchronize_session=False)
        )
        result = await self.session.execute(stmt)
        deleted = result.rowcount or 0
        log.info(
            "scan_batch.soft_delete_many_any_owner",
            requested=len(batch_ids),
            deleted=deleted,
        )
        return deleted

    async def set_share_token(self, batch_id: UUID, user_id: UUID, token: str | None) -> bool:
        """Set (or clear, with ``None``) the share token on an owned batch.

        Returns ``True`` iff a live, owned row was updated. Used for both
        creating and revoking a share link — pass a fresh token to share, pass
        ``None`` to revoke.
        """
        stmt = (
            update(ScanBatch)
            .where(
                ScanBatch.id == batch_id,
                ScanBatch.user_id == user_id,
                ScanBatch.deleted_at.is_(None),
            )
            .values(share_token=token)
            .execution_options(synchronize_session=False)
        )
        result = await self.session.execute(stmt)
        won = (result.rowcount or 0) > 0
        log.info(
            "scan_batch.set_share_token",
            batch_id=str(batch_id),
            shared=token is not None,
            updated=won,
        )
        return won

    async def get_by_share_token(self, token: str) -> ScanBatch | None:
        """Public read path: resolve a share token to its full batch graph.

        No ``user_id`` filter — the token itself is the capability. Soft-deleted
        batches are excluded so revoking a batch (delete) also kills the link.
        Eager-loads images → inferences → detections for the read-only report.
        """
        stmt = (
            select(ScanBatch)
            .where(
                ScanBatch.share_token == token,
                ScanBatch.deleted_at.is_(None),
            )
            .options(
                selectinload(ScanBatch.images)
                .selectinload(ScanImage.inferences)
                .selectinload(Inference.detections)
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
