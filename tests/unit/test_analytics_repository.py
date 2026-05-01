"""Unit tests for :class:`AnalyticsRepository`.

These verify the row-tuple shape and column ordering passed to
``ClickHouseClient.insert``. The CH client itself is mocked — the
repo's job is purely serialization, so a unit test is enough; the
integration suite covers the round-trip against a real CH container.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from seedbank.infrastructure.analytics.repository import (
    AnalyticsRepository,
    DimModelRow,
    DimSeedTypeRow,
    DimUserRow,
    FactDetectionRow,
    FactExperimentResultRow,
    FactInferenceRow,
    FactScanBatchRow,
)

pytestmark = pytest.mark.unit


# ── Helpers ────────────────────────────────────────────────────────────────


def _client() -> Any:
    fake = AsyncMock()
    fake.insert = AsyncMock()
    return fake


def _utc(year: int = 2026, month: int = 5, day: int = 1) -> datetime:
    return datetime(year, month, day, 12, 0, 0, tzinfo=timezone.utc)


# ── Dim writes ─────────────────────────────────────────────────────────────


async def test_upsert_user_writes_seven_columns() -> None:
    client = _client()
    repo = AnalyticsRepository(client)
    user_id = uuid4()
    await repo.upsert_user(
        DimUserRow(
            user_id=user_id,
            email="u@example.com",
            role="ai_developer",
            is_active=True,
            is_verified=False,
            created_at=_utc(),
            updated_at=_utc(month=6),
        )
    )

    client.insert.assert_awaited_once()
    kwargs = client.insert.await_args.kwargs
    assert kwargs["table"] == "dim_user"
    assert kwargs["column_names"] == [
        "user_id",
        "email",
        "role",
        "is_active",
        "is_verified",
        "created_at",
        "updated_at",
    ]
    [row] = kwargs["rows"]
    assert row[0] == user_id
    assert row[1] == "u@example.com"
    assert row[2] == "ai_developer"
    assert row[3] == 1  # bool → uint8
    assert row[4] == 0


async def test_upsert_seed_type_passes_threshold_as_decimal() -> None:
    client = _client()
    repo = AnalyticsRepository(client)
    await repo.upsert_seed_type(
        DimSeedTypeRow(
            seed_type_id=uuid4(),
            code="coffee",
            display_name="Coffee",
            default_confidence_threshold=Decimal("0.7000"),
            created_at=_utc(),
            updated_at=_utc(),
        )
    )
    [row] = client.insert.await_args.kwargs["rows"]
    assert isinstance(row[3], Decimal)


async def test_upsert_model_serializes_seed_type_id_nullable() -> None:
    client = _client()
    repo = AnalyticsRepository(client)
    await repo.upsert_model(
        DimModelRow(
            model_id=uuid4(),
            name="resnet18",
            version="v1",
            kind="classification",
            backend="torch_local",
            seed_type_id=None,
            status="production",
            created_at=_utc(),
            updated_at=_utc(),
        )
    )
    [row] = client.insert.await_args.kwargs["rows"]
    # seed_type_id is index 5
    assert row[5] is None


# ── Fact writes ────────────────────────────────────────────────────────────


async def test_insert_inference_row_shape() -> None:
    client = _client()
    repo = AnalyticsRepository(client)
    inf_id, image_id, batch_id, user_id, model_id = (uuid4() for _ in range(5))
    await repo.insert_inference(
        FactInferenceRow(
            inference_id=inf_id,
            image_id=image_id,
            batch_id=batch_id,
            user_id=user_id,
            model_id=model_id,
            seed_type_id=None,
            backend="torch_local",
            model_kind="detection",
            latency_ms=42,
            has_error=False,
            occurred_at=_utc(),
        )
    )
    kwargs = client.insert.await_args.kwargs
    assert kwargs["table"] == "fact_inference"
    [row] = kwargs["rows"]
    assert row[0] == inf_id
    assert row[6] == "torch_local"
    assert row[7] == "detection"
    assert row[8] == 42
    assert row[9] == 0  # has_error → 0
    # timestamp coerced to aware UTC
    assert isinstance(row[10], datetime)
    assert row[10].tzinfo is timezone.utc


async def test_insert_inference_naive_datetime_promotes_to_utc() -> None:
    client = _client()
    repo = AnalyticsRepository(client)
    naive = datetime(2026, 1, 1, 0, 0, 0)
    await repo.insert_inference(
        FactInferenceRow(
            inference_id=uuid4(),
            image_id=uuid4(),
            batch_id=uuid4(),
            user_id=uuid4(),
            model_id=uuid4(),
            seed_type_id=None,
            backend="roboflow",
            model_kind="detection",
            latency_ms=None,
            has_error=True,
            occurred_at=naive,
        )
    )
    [row] = client.insert.await_args.kwargs["rows"]
    assert row[8] is None
    assert row[9] == 1  # has_error
    assert row[10].tzinfo is timezone.utc


async def test_insert_detections_empty_skips_call() -> None:
    client = _client()
    repo = AnalyticsRepository(client)
    await repo.insert_detections([])
    client.insert.assert_not_awaited()


async def test_insert_detections_serializes_quality_and_decimals() -> None:
    client = _client()
    repo = AnalyticsRepository(client)
    det = FactDetectionRow(
        detection_id=uuid4(),
        inference_id=uuid4(),
        image_id=uuid4(),
        batch_id=uuid4(),
        user_id=uuid4(),
        model_id=uuid4(),
        seed_type_id=uuid4(),
        quality="good",
        confidence=Decimal("0.9123"),
        detection_confidence=Decimal("0.9123"),
        box_x_norm=Decimal("0.123456"),
        box_y_norm=Decimal("0.234567"),
        box_w_norm=Decimal("0.345678"),
        box_h_norm=Decimal("0.456789"),
        width_px=80,
        height_px=100,
        area_px=8000,
        aspect_ratio=Decimal("0.8000"),
        occurred_at=_utc(),
    )
    await repo.insert_detections([det])
    [row] = client.insert.await_args.kwargs["rows"]
    assert row[7] == "good"  # quality
    assert row[8] == Decimal("0.9123")  # confidence


async def test_insert_experiment_results_writes_has_error_flag() -> None:
    client = _client()
    repo = AnalyticsRepository(client)
    rows = [
        FactExperimentResultRow(
            result_id=uuid4(),
            experiment_id=uuid4(),
            dataset_id=uuid4(),
            dataset_item_id=uuid4(),
            model_id=uuid4(),
            user_id=uuid4(),
            has_error=True,
            latency_ms=None,
            occurred_at=_utc(),
        ),
        FactExperimentResultRow(
            result_id=uuid4(),
            experiment_id=uuid4(),
            dataset_id=uuid4(),
            dataset_item_id=uuid4(),
            model_id=uuid4(),
            user_id=uuid4(),
            has_error=False,
            latency_ms=42,
            occurred_at=_utc(),
        ),
    ]
    await repo.insert_experiment_results(rows)
    payload = client.insert.await_args.kwargs["rows"]
    assert [r[6] for r in payload] == [1, 0]
    assert [r[7] for r in payload] == [None, 42]


async def test_upsert_scan_batch_passes_geo_and_status() -> None:
    client = _client()
    repo = AnalyticsRepository(client)
    bid = uuid4()
    await repo.upsert_scan_batch(
        FactScanBatchRow(
            batch_id=bid,
            user_id=uuid4(),
            supplier_id=None,
            status="succeeded",
            source="api",
            image_count=3,
            duration_ms=1234,
            submitted_at=_utc(),
            started_at=_utc(),
            finished_at=_utc(),
            geo_country_code="EG",
        )
    )
    [row] = client.insert.await_args.kwargs["rows"]
    assert row[0] == bid
    assert row[3] == "succeeded"
    assert row[10] == "EG"


async def test_upsert_scan_batch_handles_pending_with_no_started_at() -> None:
    client = _client()
    repo = AnalyticsRepository(client)
    await repo.upsert_scan_batch(
        FactScanBatchRow(
            batch_id=uuid4(),
            user_id=uuid4(),
            supplier_id=None,
            status="pending",
            source="api",
            image_count=0,
            duration_ms=None,
            submitted_at=_utc(),
            started_at=None,
            finished_at=None,
            geo_country_code="",
        )
    )
    [row] = client.insert.await_args.kwargs["rows"]
    assert row[8] is None  # started_at
    assert row[9] is None  # finished_at
