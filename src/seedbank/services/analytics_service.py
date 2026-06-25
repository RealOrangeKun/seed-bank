"""Analytics service — assembles the ``/api/v1/analytics`` payload.

Owns the presentation-shaping the repository shouldn't: deriving rates,
densifying the trend line so the chart has one point per day in the window
(SQL only returns days with activity), and padding the confidence histogram to
all ten buckets. Pure aggregation read path — no writes, so no commit.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from seedbank.core.logging import get_logger
from seedbank.schemas.analysis import BatchCompareOut, BatchCompareRow
from seedbank.schemas.analytics import (
    AnalyticsConfidenceBin,
    AnalyticsOut,
    AnalyticsTotals,
    AnalyticsTrendPoint,
    AnalyticsTypeSplit,
)

if TYPE_CHECKING:
    from uuid import UUID

    from seedbank.infrastructure.db.repositories import AnalyticsRepository

log = get_logger(__name__)

# Clamp the trend window so a caller can't ask for an unbounded range.
_MIN_WINDOW_DAYS = 1
_MAX_WINDOW_DAYS = 365


class AnalyticsService:
    def __init__(self, *, analytics: AnalyticsRepository) -> None:
        self.analytics = analytics

    async def summary(self, *, user_id: UUID, window_days: int = 30) -> AnalyticsOut:
        window = max(_MIN_WINDOW_DAYS, min(_MAX_WINDOW_DAYS, window_days))
        now = datetime.now(UTC)
        since = now - timedelta(days=window - 1)
        # Normalize to the start of the first day so the trend window is whole days.
        since = since.replace(hour=0, minute=0, second=0, microsecond=0)

        totals = await self.analytics.totals(user_id)
        trend_rows = await self.analytics.trend(user_id, since=since, until=now)
        type_rows = await self.analytics.type_split(user_id)
        conf_rows = await self.analytics.confidence_histogram(user_id)

        classified = totals.good + totals.bad
        unclassified = totals.detections - classified
        totals_out = AnalyticsTotals(
            batches=totals.batches,
            images=totals.images,
            detections=totals.detections,
            good=totals.good,
            bad=totals.bad,
            unclassified=unclassified,
            good_rate=(totals.good / classified) if classified else 0.0,
        )

        # Densify the trend: one point per day across the window, zero-filled.
        by_day = {r.day: r for r in trend_rows}
        start_day = since.date()
        trend_out: list[AnalyticsTrendPoint] = []
        for offset in range(window):
            d = start_day + timedelta(days=offset)
            row = by_day.get(d)
            trend_out.append(
                AnalyticsTrendPoint(
                    day=d,
                    batches=row.batches if row else 0,
                    detections=row.detections if row else 0,
                )
            )

        type_out = [
            AnalyticsTypeSplit(
                seed_type_id=r.seed_type_id,
                total=r.total,
                good=r.good,
                bad=r.bad,
                good_rate=(r.good / (r.good + r.bad)) if (r.good + r.bad) else 0.0,
            )
            for r in type_rows
        ]

        # Pad the histogram to all ten 10%-wide buckets.
        counts = {r.bucket: r.count for r in conf_rows}
        hist_out = [
            AnalyticsConfidenceBin(
                from_pct=i * 10,
                to_pct=(i + 1) * 10,
                count=counts.get(i, 0),
            )
            for i in range(10)
        ]

        return AnalyticsOut(
            totals=totals_out,
            trend=trend_out,
            type_split=type_out,
            confidence_histogram=hist_out,
            window_days=window,
        )

    async def compare(self, *, batch_ids: list[UUID], user_id: UUID) -> BatchCompareOut:
        """Side-by-side aggregate stats for the caller's batches.

        Rows come back in the order requested; ids the caller doesn't own (or
        that don't exist) are reported in ``missing`` rather than raising, so a
        partially-stale selection still returns useful data. De-duplicates the
        request so a repeated id can't appear twice.
        """
        # Preserve request order while de-duplicating.
        ordered_ids = list(dict.fromkeys(batch_ids))
        stats = await self.analytics.batch_stats(ordered_ids, user_id)
        by_id = {s.batch_id: s for s in stats}

        rows: list[BatchCompareRow] = []
        missing: list[UUID] = []
        for bid in ordered_ids:
            s = by_id.get(bid)
            if s is None:
                missing.append(bid)
                continue
            classified = s.good + s.bad
            rows.append(
                BatchCompareRow(
                    batch_id=s.batch_id,
                    images=s.images,
                    detections=s.detections,
                    good=s.good,
                    bad=s.bad,
                    unclassified=s.detections - classified,
                    good_rate=(s.good / classified) if classified else 0.0,
                    mean_confidence=s.mean_confidence,
                )
            )
        return BatchCompareOut(rows=rows, missing=missing)


__all__ = ["AnalyticsService"]
