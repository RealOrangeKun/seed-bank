"""Unit tests for ``AnalyticsService`` — densification, rates, and compare.

The repository is mocked (returns dataclass rows); these pin the service-layer
shaping the repo doesn't do: per-day trend densification across the window,
good-rate over *classified* only, histogram padding to ten buckets, and the
compare ordering / missing / de-dup contract. No DB.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from seedbank.infrastructure.db.repositories.analytics import (
    BatchStats,
    ConfidenceBin,
    Totals,
    TrendPoint,
    TypeSplitRow,
)
from seedbank.services.analytics_service import AnalyticsService

pytestmark = pytest.mark.unit


def _service(
    *,
    totals: Totals,
    trend: list[TrendPoint] | None = None,
    type_split: list[TypeSplitRow] | None = None,
    histogram: list[ConfidenceBin] | None = None,
    batch_stats: list[BatchStats] | None = None,
) -> AnalyticsService:
    repo = MagicMock()
    repo.totals = AsyncMock(return_value=totals)
    repo.trend = AsyncMock(return_value=trend or [])
    repo.type_split = AsyncMock(return_value=type_split or [])
    repo.confidence_histogram = AsyncMock(return_value=histogram or [])
    repo.batch_stats = AsyncMock(return_value=batch_stats or [])
    return AnalyticsService(analytics=repo)


class TestSummary:
    async def test_trend_is_densified_to_one_point_per_day(self) -> None:
        svc = _service(totals=Totals(0, 0, 0, 0, 0))
        out = await svc.summary(user_id=uuid4(), window_days=14)
        assert len(out.trend) == 14
        # Contiguous days, ascending.
        days = [p.day for p in out.trend]
        assert days == sorted(days)
        assert (days[-1] - days[0]) == timedelta(days=13)

    async def test_window_is_clamped(self) -> None:
        svc = _service(totals=Totals(0, 0, 0, 0, 0))
        assert (await svc.summary(user_id=uuid4(), window_days=9999)).window_days == 365
        assert (await svc.summary(user_id=uuid4(), window_days=0)).window_days == 1

    async def test_good_rate_is_over_classified_only(self) -> None:
        # 6 detections: 3 good, 1 bad, 2 unclassified → good_rate = 3/4.
        svc = _service(totals=Totals(batches=1, images=1, detections=6, good=3, bad=1))
        out = await svc.summary(user_id=uuid4(), window_days=7)
        assert out.totals.unclassified == 2
        assert out.totals.good_rate == pytest.approx(0.75)

    async def test_histogram_is_padded_to_ten_buckets(self) -> None:
        svc = _service(
            totals=Totals(0, 0, 0, 0, 0),
            histogram=[ConfidenceBin(bucket=9, count=5)],
        )
        out = await svc.summary(user_id=uuid4(), window_days=7)
        assert len(out.confidence_histogram) == 10
        assert out.confidence_histogram[9].count == 5
        assert out.confidence_histogram[0].count == 0
        # Bounds are 0–100 in 10% steps.
        assert out.confidence_histogram[0].from_pct == 0
        assert out.confidence_histogram[9].to_pct == 100

    async def test_known_trend_day_carries_its_counts(self) -> None:
        # Use the service's own UTC-based last day rather than local date.today()
        # so this is robust across the local/UTC day boundary.
        from datetime import UTC, datetime

        day = datetime.now(UTC).date()
        svc = _service(
            totals=Totals(0, 0, 0, 0, 0),
            trend=[TrendPoint(day=day, batches=3, detections=20)],
        )
        out = await svc.summary(user_id=uuid4(), window_days=7)
        match = [p for p in out.trend if p.day == day]
        assert match and match[0].batches == 3 and match[0].detections == 20

    async def test_type_split_good_rate(self) -> None:
        tid = uuid4()
        svc = _service(
            totals=Totals(0, 0, 0, 0, 0),
            type_split=[TypeSplitRow(seed_type_id=tid, total=10, good=8, bad=2)],
        )
        out = await svc.summary(user_id=uuid4(), window_days=7)
        assert out.type_split[0].good_rate == pytest.approx(0.8)


class TestCompare:
    async def test_rows_in_request_order_missing_reported(self) -> None:
        a, b, c = uuid4(), uuid4(), uuid4()
        # Repo returns only a and c (b is unowned/unknown).
        svc = _service(
            totals=Totals(0, 0, 0, 0, 0),
            batch_stats=[
                BatchStats(c, images=1, detections=2, good=1, bad=1, mean_confidence=0.5),
                BatchStats(a, images=2, detections=4, good=4, bad=0, mean_confidence=0.9),
            ],
        )
        out = await svc.compare(batch_ids=[a, b, c], user_id=uuid4())
        # Order preserved as requested (a, then c); b missing.
        assert [r.batch_id for r in out.rows] == [a, c]
        assert out.missing == [b]

    async def test_good_rate_and_unclassified_derived(self) -> None:
        a = uuid4()
        svc = _service(
            totals=Totals(0, 0, 0, 0, 0),
            batch_stats=[BatchStats(a, images=1, detections=5, good=3, bad=1, mean_confidence=0.7)],
        )
        out = await svc.compare(batch_ids=[a], user_id=uuid4())
        row = out.rows[0]
        assert row.unclassified == 1  # 5 - (3+1)
        assert row.good_rate == pytest.approx(0.75)  # 3/(3+1)

    async def test_duplicate_ids_deduped(self) -> None:
        a = uuid4()
        repo_calls: list[list] = []
        svc = _service(
            totals=Totals(0, 0, 0, 0, 0),
            batch_stats=[BatchStats(a, images=1, detections=0, good=0, bad=0, mean_confidence=0.0)],
        )
        svc.analytics.batch_stats = AsyncMock(
            side_effect=lambda ids, uid: repo_calls.append(ids) or [BatchStats(a, 1, 0, 0, 0, 0.0)]
        )
        await svc.compare(batch_ids=[a, a, a], user_id=uuid4())
        assert repo_calls[0] == [a]  # de-duped before the repo call
