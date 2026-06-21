"""Response DTOs for ``GET /api/v1/analytics``.

The service computes these from the OLTP repository aggregations; the router
wraps the top-level object in an ``Envelope``. Counts are plain ints; rates are
floats in ``[0, 1]`` (the frontend formats as percentages).
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class AnalyticsTotals(BaseModel):
    batches: int
    images: int
    detections: int
    good: int
    bad: int
    unclassified: int
    good_rate: float


class AnalyticsTrendPoint(BaseModel):
    day: date
    batches: int
    detections: int


class AnalyticsTypeSplit(BaseModel):
    seed_type_id: UUID | None = None
    total: int
    good: int
    bad: int
    good_rate: float


class AnalyticsConfidenceBin(BaseModel):
    """A 10%-wide bucket; ``from_pct``/``to_pct`` are 0-100 inclusive bounds."""

    from_pct: int
    to_pct: int
    count: int


class AnalyticsOut(BaseModel):
    """The full analytics payload for one user."""

    totals: AnalyticsTotals
    trend: list[AnalyticsTrendPoint]
    type_split: list[AnalyticsTypeSplit]
    confidence_histogram: list[AnalyticsConfidenceBin]
    window_days: int


__all__ = [
    "AnalyticsConfidenceBin",
    "AnalyticsOut",
    "AnalyticsTotals",
    "AnalyticsTrendPoint",
    "AnalyticsTypeSplit",
]
