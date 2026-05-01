"""Write surface for the OLAP star schema.

Phase 8 ships **app-level dual-write** rather than log-based CDC: after
each OLTP commit, a Celery task in :mod:`seedbank.workers.tasks.dwh`
dispatches an idempotent insert through this repository. ClickHouse's
``ReplacingMergeTree`` engine de-dups on the sort key at merge time,
which means at-least-once delivery is safe — duplicate inserts collapse.

The repository is intentionally thin: it knows the column order for each
table and serializes Python values into the row tuples
``clickhouse-connect`` expects. Domain decisions (which model_id to
join, what counts as "has_error") happen in the worker tasks.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from seedbank.infrastructure.analytics.clickhouse_client import ClickHouseClient


# ── Row dataclasses ─────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class DimUserRow:
    user_id: UUID
    email: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class DimSeedTypeRow:
    seed_type_id: UUID
    code: str
    display_name: str
    default_confidence_threshold: Decimal
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class DimModelRow:
    model_id: UUID
    name: str
    version: str
    kind: str
    backend: str
    seed_type_id: UUID | None
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class FactInferenceRow:
    inference_id: UUID
    image_id: UUID
    batch_id: UUID
    user_id: UUID
    model_id: UUID
    seed_type_id: UUID | None
    backend: str
    model_kind: str
    latency_ms: int | None
    has_error: bool
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class FactDetectionRow:
    detection_id: UUID
    inference_id: UUID
    image_id: UUID
    batch_id: UUID
    user_id: UUID
    model_id: UUID
    seed_type_id: UUID | None
    quality: str | None
    confidence: Decimal
    detection_confidence: Decimal
    box_x_norm: Decimal
    box_y_norm: Decimal
    box_w_norm: Decimal
    box_h_norm: Decimal
    width_px: int | None
    height_px: int | None
    area_px: int | None
    aspect_ratio: Decimal | None
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class FactExperimentResultRow:
    result_id: UUID
    experiment_id: UUID
    dataset_id: UUID
    dataset_item_id: UUID
    model_id: UUID
    user_id: UUID | None
    has_error: bool
    latency_ms: int | None
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class FactScanBatchRow:
    batch_id: UUID
    user_id: UUID
    supplier_id: UUID | None
    status: str
    source: str
    image_count: int
    duration_ms: int | None
    submitted_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    geo_country_code: str  # '' when null at source


# ── Column orders (match schema.sql) ────────────────────────────────────────

_DIM_USER_COLS = [
    "user_id",
    "email",
    "role",
    "is_active",
    "is_verified",
    "created_at",
    "updated_at",
]
_DIM_SEED_TYPE_COLS = [
    "seed_type_id",
    "code",
    "display_name",
    "default_confidence_threshold",
    "created_at",
    "updated_at",
]
_DIM_MODEL_COLS = [
    "model_id",
    "name",
    "version",
    "kind",
    "backend",
    "seed_type_id",
    "status",
    "created_at",
    "updated_at",
]
_FACT_INFERENCE_COLS = [
    "inference_id",
    "image_id",
    "batch_id",
    "user_id",
    "model_id",
    "seed_type_id",
    "backend",
    "model_kind",
    "latency_ms",
    "has_error",
    "occurred_at",
]
_FACT_DETECTION_COLS = [
    "detection_id",
    "inference_id",
    "image_id",
    "batch_id",
    "user_id",
    "model_id",
    "seed_type_id",
    "quality",
    "confidence",
    "detection_confidence",
    "box_x_norm",
    "box_y_norm",
    "box_w_norm",
    "box_h_norm",
    "width_px",
    "height_px",
    "area_px",
    "aspect_ratio",
    "occurred_at",
]
_FACT_EXPERIMENT_RESULT_COLS = [
    "result_id",
    "experiment_id",
    "dataset_id",
    "dataset_item_id",
    "model_id",
    "user_id",
    "has_error",
    "latency_ms",
    "occurred_at",
]
_FACT_SCAN_BATCH_COLS = [
    "batch_id",
    "user_id",
    "supplier_id",
    "status",
    "source",
    "image_count",
    "duration_ms",
    "submitted_at",
    "started_at",
    "finished_at",
    "geo_country_code",
]


def _aware_utc(dt: datetime) -> datetime:
    """ClickHouse columns are ``DateTime64(3, 'UTC')``; coerce naive
    timestamps so the driver doesn't drop the offset."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _opt_aware_utc(dt: datetime | None) -> datetime | None:
    return _aware_utc(dt) if dt is not None else None


# ── Repository ──────────────────────────────────────────────────────────────


class AnalyticsRepository:
    """Insert helper for dimension and fact tables.

    All methods accept either a single typed row or an iterable thereof,
    and are no-ops on empty input. ClickHouse de-dups on the sort key at
    merge time, so callers don't need to coordinate "first write vs
    update" — every call is an upsert.
    """

    def __init__(self, client: ClickHouseClient) -> None:
        self._ch = client

    # ── Dimensions ──

    async def upsert_user(self, row: DimUserRow) -> None:
        await self._ch.insert(
            table="dim_user",
            rows=[
                [
                    row.user_id,
                    row.email,
                    row.role,
                    1 if row.is_active else 0,
                    1 if row.is_verified else 0,
                    _aware_utc(row.created_at),
                    _aware_utc(row.updated_at),
                ]
            ],
            column_names=_DIM_USER_COLS,
        )

    async def upsert_seed_type(self, row: DimSeedTypeRow) -> None:
        await self._ch.insert(
            table="dim_seed_type",
            rows=[
                [
                    row.seed_type_id,
                    row.code,
                    row.display_name,
                    row.default_confidence_threshold,
                    _aware_utc(row.created_at),
                    _aware_utc(row.updated_at),
                ]
            ],
            column_names=_DIM_SEED_TYPE_COLS,
        )

    async def upsert_seed_types(self, rows: Iterable[DimSeedTypeRow]) -> None:
        payload = [
            [
                r.seed_type_id,
                r.code,
                r.display_name,
                r.default_confidence_threshold,
                _aware_utc(r.created_at),
                _aware_utc(r.updated_at),
            ]
            for r in rows
        ]
        if not payload:
            return
        await self._ch.insert(table="dim_seed_type", rows=payload, column_names=_DIM_SEED_TYPE_COLS)

    async def upsert_model(self, row: DimModelRow) -> None:
        await self._ch.insert(
            table="dim_model",
            rows=[
                [
                    row.model_id,
                    row.name,
                    row.version,
                    row.kind,
                    row.backend,
                    row.seed_type_id,
                    row.status,
                    _aware_utc(row.created_at),
                    _aware_utc(row.updated_at),
                ]
            ],
            column_names=_DIM_MODEL_COLS,
        )

    # ── Facts ──

    async def insert_inference(self, row: FactInferenceRow) -> None:
        await self._ch.insert(
            table="fact_inference",
            rows=[
                [
                    row.inference_id,
                    row.image_id,
                    row.batch_id,
                    row.user_id,
                    row.model_id,
                    row.seed_type_id,
                    row.backend,
                    row.model_kind,
                    row.latency_ms,
                    1 if row.has_error else 0,
                    _aware_utc(row.occurred_at),
                ]
            ],
            column_names=_FACT_INFERENCE_COLS,
        )

    async def insert_detections(self, rows: Iterable[FactDetectionRow]) -> None:
        payload: list[list[Any]] = [
            [
                r.detection_id,
                r.inference_id,
                r.image_id,
                r.batch_id,
                r.user_id,
                r.model_id,
                r.seed_type_id,
                r.quality,
                r.confidence,
                r.detection_confidence,
                r.box_x_norm,
                r.box_y_norm,
                r.box_w_norm,
                r.box_h_norm,
                r.width_px,
                r.height_px,
                r.area_px,
                r.aspect_ratio,
                _aware_utc(r.occurred_at),
            ]
            for r in rows
        ]
        if not payload:
            return
        await self._ch.insert(
            table="fact_detection", rows=payload, column_names=_FACT_DETECTION_COLS
        )

    async def insert_experiment_results(self, rows: Iterable[FactExperimentResultRow]) -> None:
        payload: list[list[Any]] = [
            [
                r.result_id,
                r.experiment_id,
                r.dataset_id,
                r.dataset_item_id,
                r.model_id,
                r.user_id,
                1 if r.has_error else 0,
                r.latency_ms,
                _aware_utc(r.occurred_at),
            ]
            for r in rows
        ]
        if not payload:
            return
        await self._ch.insert(
            table="fact_experiment_result",
            rows=payload,
            column_names=_FACT_EXPERIMENT_RESULT_COLS,
        )

    async def upsert_scan_batch(self, row: FactScanBatchRow) -> None:
        await self._ch.insert(
            table="fact_scan_batch",
            rows=[
                [
                    row.batch_id,
                    row.user_id,
                    row.supplier_id,
                    row.status,
                    row.source,
                    row.image_count,
                    row.duration_ms,
                    _aware_utc(row.submitted_at),
                    _opt_aware_utc(row.started_at),
                    _opt_aware_utc(row.finished_at),
                    row.geo_country_code,
                ]
            ],
            column_names=_FACT_SCAN_BATCH_COLS,
        )


__all__ = [
    "AnalyticsRepository",
    "DimModelRow",
    "DimSeedTypeRow",
    "DimUserRow",
    "FactDetectionRow",
    "FactExperimentResultRow",
    "FactInferenceRow",
    "FactScanBatchRow",
]
