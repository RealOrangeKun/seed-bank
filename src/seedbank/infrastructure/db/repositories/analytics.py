"""Analytics repository — read-only OLTP aggregations for ``/api/v1/analytics``.

Computes user-scoped summaries straight from the transactional tables
(``scan_batches`` → ``scan_images`` → ``inferences`` → ``seed_detections``).
This deliberately does NOT touch the ClickHouse DWH: the OLTP volume per user
is small (hundreds of batches), the dual-write warehouse is optional infra, and
keeping analytics on Postgres means the endpoint works in every environment.

Every query filters ``scan_batches.user_id`` and excludes soft-deleted batches,
mirroring the ownership rules of the rest of the batch read paths. All grouping
happens in SQL — no per-row Python aggregation, no N+1.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, case, cast, func, select

from seedbank.core.logging import get_logger
from seedbank.infrastructure.db.models import (
    Inference,
    ScanBatch,
    ScanImage,
    SeedDetection,
)

from .base import Repository

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy import ScalarSelect

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Totals:
    """Headline counters for a user's whole (live) history."""

    batches: int
    images: int
    detections: int
    good: int
    bad: int


@dataclass(frozen=True, slots=True)
class TrendPoint:
    """One day's activity for the trend line."""

    day: date
    batches: int
    detections: int


@dataclass(frozen=True, slots=True)
class TypeSplitRow:
    """Per-seed-type good/bad split."""

    seed_type_id: UUID | None
    total: int
    good: int
    bad: int


@dataclass(frozen=True, slots=True)
class ConfidenceBin:
    """One 10%-wide confidence bucket (0 ≤ index ≤ 9)."""

    bucket: int
    count: int


@dataclass(frozen=True, slots=True)
class BatchStats:
    """Aggregate detection stats for a single batch (compare view)."""

    batch_id: UUID
    images: int
    detections: int
    good: int
    bad: int
    mean_confidence: float


class AnalyticsRepository(Repository[ScanBatch]):
    model = ScanBatch

    def _live_batch_ids(self, user_id: UUID) -> ScalarSelect[UUID]:
        """Subquery of the user's non-deleted batch ids — the spine every
        aggregation joins against so soft-deleted batches never leak in."""
        return (
            select(ScanBatch.id)
            .where(ScanBatch.user_id == user_id, ScanBatch.deleted_at.is_(None))
            .scalar_subquery()
        )

    async def totals(self, user_id: UUID) -> Totals:
        """Lifetime counters in a small number of grouped queries."""
        live = self._live_batch_ids(user_id)

        batch_count = (
            await self.session.execute(
                select(func.count())
                .select_from(ScanBatch)
                .where(ScanBatch.user_id == user_id, ScanBatch.deleted_at.is_(None))
            )
        ).scalar_one()

        image_count = (
            await self.session.execute(
                select(func.count(ScanImage.id)).where(ScanImage.batch_id.in_(live))
            )
        ).scalar_one()

        # Detections + good/bad in one pass via FILTER-style conditional counts.
        det_row = (
            await self.session.execute(
                select(
                    func.count(SeedDetection.id),
                    func.count(case((SeedDetection.quality == "good", 1))),
                    func.count(case((SeedDetection.quality == "bad", 1))),
                )
                .select_from(SeedDetection)
                .join(Inference, SeedDetection.inference_id == Inference.id)
                .join(ScanImage, Inference.image_id == ScanImage.id)
                .where(ScanImage.batch_id.in_(live))
            )
        ).one()

        return Totals(
            batches=int(batch_count),
            images=int(image_count),
            detections=int(det_row[0]),
            good=int(det_row[1]),
            bad=int(det_row[2]),
        )

    async def trend(self, user_id: UUID, *, since: datetime, until: datetime) -> list[TrendPoint]:
        """Per-day batch + detection counts within ``[since, until]``.

        Days with no activity are omitted (the caller densifies for the chart).
        Grouped by the batch's submission date so the spine is the batch, and
        detections are counted via a LEFT JOIN so empty batches still register a
        day with zero detections.
        """
        day = cast(ScanBatch.submitted_at, Date).label("day")
        stmt = (
            select(
                day,
                func.count(func.distinct(ScanBatch.id)),
                func.count(SeedDetection.id),
            )
            .select_from(ScanBatch)
            .outerjoin(ScanImage, ScanImage.batch_id == ScanBatch.id)
            .outerjoin(Inference, Inference.image_id == ScanImage.id)
            .outerjoin(SeedDetection, SeedDetection.inference_id == Inference.id)
            .where(
                ScanBatch.user_id == user_id,
                ScanBatch.deleted_at.is_(None),
                ScanBatch.submitted_at >= since,
                ScanBatch.submitted_at <= until,
            )
            .group_by(day)
            .order_by(day)
        )
        rows = (await self.session.execute(stmt)).all()
        return [TrendPoint(day=r[0], batches=int(r[1]), detections=int(r[2])) for r in rows]

    async def type_split(self, user_id: UUID) -> list[TypeSplitRow]:
        """Per-seed-type good/bad/total counts across the user's live batches."""
        live = self._live_batch_ids(user_id)
        stmt = (
            select(
                SeedDetection.seed_type_id,
                func.count(SeedDetection.id),
                func.count(case((SeedDetection.quality == "good", 1))),
                func.count(case((SeedDetection.quality == "bad", 1))),
            )
            .select_from(SeedDetection)
            .join(Inference, SeedDetection.inference_id == Inference.id)
            .join(ScanImage, Inference.image_id == ScanImage.id)
            .where(ScanImage.batch_id.in_(live))
            .group_by(SeedDetection.seed_type_id)
            .order_by(func.count(SeedDetection.id).desc())
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            TypeSplitRow(seed_type_id=r[0], total=int(r[1]), good=int(r[2]), bad=int(r[3]))
            for r in rows
        ]

    async def confidence_histogram(self, user_id: UUID) -> list[ConfidenceBin]:
        """Ten 10%-wide confidence buckets across all detections.

        ``LEAST(9, FLOOR(confidence * 10))`` keeps a confidence of exactly 1.0
        in the last bucket. Empty buckets are filled in by the caller.
        """
        live = self._live_batch_ids(user_id)
        bucket = func.least(9, func.floor(SeedDetection.confidence * 10)).label("bucket")
        stmt = (
            select(bucket, func.count(SeedDetection.id))
            .select_from(SeedDetection)
            .join(Inference, SeedDetection.inference_id == Inference.id)
            .join(ScanImage, Inference.image_id == ScanImage.id)
            .where(ScanImage.batch_id.in_(live))
            .group_by(bucket)
            .order_by(bucket)
        )
        rows = (await self.session.execute(stmt)).all()
        return [ConfidenceBin(bucket=int(r[0]), count=int(r[1])) for r in rows]

    async def batch_stats(self, batch_ids: list[UUID], user_id: UUID) -> list[BatchStats]:
        """Per-batch aggregate detection stats for the compare view.

        Only the caller's own, non-deleted batches in ``batch_ids`` are
        returned; ids the user doesn't own (or that don't exist) are silently
        absent, so the service can detect a partial/empty selection. One grouped
        query — image and detection counts both come from LEFT JOINs so a batch
        with no images still yields a row with zeros.
        """
        if not batch_ids:
            return []
        # Count distinct images and detections separately to avoid the join
        # fan-out inflating the image count once detections multiply rows.
        stmt = (
            select(
                ScanBatch.id,
                func.count(func.distinct(ScanImage.id)),
                func.count(SeedDetection.id),
                func.count(case((SeedDetection.quality == "good", 1))),
                func.count(case((SeedDetection.quality == "bad", 1))),
                func.coalesce(func.avg(SeedDetection.confidence), 0),
            )
            .select_from(ScanBatch)
            .outerjoin(ScanImage, ScanImage.batch_id == ScanBatch.id)
            .outerjoin(Inference, Inference.image_id == ScanImage.id)
            .outerjoin(SeedDetection, SeedDetection.inference_id == Inference.id)
            .where(
                ScanBatch.id.in_(batch_ids),
                ScanBatch.user_id == user_id,
                ScanBatch.deleted_at.is_(None),
            )
            .group_by(ScanBatch.id)
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            BatchStats(
                batch_id=r[0],
                images=int(r[1]),
                detections=int(r[2]),
                good=int(r[3]),
                bad=int(r[4]),
                mean_confidence=float(r[5]),
            )
            for r in rows
        ]


__all__ = [
    "AnalyticsRepository",
    "BatchStats",
    "ConfidenceBin",
    "Totals",
    "TrendPoint",
    "TypeSplitRow",
]
