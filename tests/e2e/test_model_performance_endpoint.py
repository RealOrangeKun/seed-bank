"""End-to-end coverage for ``GET /api/v1/models/{id}/performance``.

Pins the offline-metrics half of the response (Phase 7). The ClickHouse
half is exercised in the existing models tests; here we just confirm
that ``model_metrics`` rows surface via ``offline_metrics`` and that the
endpoint stays role-gated.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from seedbank.core.ids import uuid7
from seedbank.infrastructure.db.enums import ModelBackend, ModelKind, ModelStatus
from seedbank.infrastructure.db.models import (
    Dataset,
    ModelArtifact,
    ModelMetric,
)
from tests.e2e.conftest import SeededUser, auth_header

# The endpoint injects ``ClickHouseDep``; wire a real ClickHouse testcontainer
# (and reset the cached process-wide client) so injection connects instead of
# dialing the compose hostname ``clickhouse:8123``.
pytestmark = [pytest.mark.e2e, pytest.mark.usefixtures("clickhouse_client")]


async def _seed_model_with_metrics(
    db_session: AsyncSession,
) -> tuple[ModelArtifact, Dataset]:
    model = ModelArtifact(
        id=uuid7(),
        name="m-perf",
        version="v1",
        kind=ModelKind.DETECTION.value,
        backend=ModelBackend.TORCH_LOCAL.value,
        artifact_uri="m-perf/v1/weights.pth",
        status=ModelStatus.PRODUCTION.value,
    )
    dataset = Dataset(
        id=uuid7(),
        name=f"ds-perf-{uuid4().hex[:6]}",
    )
    db_session.add(model)
    db_session.add(dataset)
    await db_session.flush()

    for name, value in [
        ("precision", Decimal("0.900000")),
        ("recall", Decimal("0.800000")),
        ("f1", Decimal("0.847000")),
        ("mean_latency_ms", Decimal("12.500000")),
    ]:
        db_session.add(
            ModelMetric(
                model_id=model.id,
                dataset_id=dataset.id,
                metric_name=name,
                metric_value=value,
            )
        )
    await db_session.commit()
    return model, dataset


async def test_performance_returns_offline_metrics(
    app_client: AsyncClient,
    ai_dev: SeededUser,
    db_session: AsyncSession,
) -> None:
    model, dataset = await _seed_model_with_metrics(db_session)

    r = await app_client.get(
        f"/api/v1/models/{model.id}/performance",
        headers=auth_header(ai_dev.token),
    )
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    assert body["model_id"] == str(model.id)

    offline = {m["metric_name"]: m for m in body["offline_metrics"]}
    assert "precision" in offline
    assert offline["precision"]["metric_value"] == pytest.approx(0.9)
    assert offline["precision"]["dataset_id"] == str(dataset.id)
    assert {"recall", "f1", "mean_latency_ms"}.issubset(offline.keys())


async def test_performance_404_on_missing_model(
    app_client: AsyncClient, ai_dev: SeededUser
) -> None:
    r = await app_client.get(
        f"/api/v1/models/{uuid4()}/performance",
        headers=auth_header(ai_dev.token),
    )
    assert r.status_code == 404


async def test_performance_403_for_end_user(
    app_client: AsyncClient,
    end_user: SeededUser,
    db_session: AsyncSession,
) -> None:
    model, _ = await _seed_model_with_metrics(db_session)
    r = await app_client.get(
        f"/api/v1/models/{model.id}/performance",
        headers=auth_header(end_user.token),
    )
    assert r.status_code == 403
