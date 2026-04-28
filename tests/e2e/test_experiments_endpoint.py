"""End-to-end coverage for ``/api/v1/experiments``.

Pins the create + list + detail surface and the role gate. The Celery
``send_task`` is short-circuited so the dispatch never reaches a broker;
the worker itself is exercised separately in Chunk 3 / integration tests.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from seedbank.core.ids import uuid7
from seedbank.infrastructure.db.enums import ModelBackend, ModelKind, ModelStatus
from seedbank.infrastructure.db.models import Dataset, ModelArtifact
from tests.e2e.conftest import SeededUser, auth_header

pytestmark = pytest.mark.e2e


@pytest.fixture(autouse=True)
def _short_circuit_celery(monkeypatch: pytest.MonkeyPatch) -> None:
    from seedbank.workers import celery_app as celery_module

    def _fake_send_task(*args: Any, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr(celery_module.celery_app, "send_task", _fake_send_task)


async def _seed_model_and_dataset(
    db_session: AsyncSession,
    *,
    model_status: str = ModelStatus.PRODUCTION.value,
) -> tuple[ModelArtifact, Dataset]:
    """Insert a usable model_artifact + dataset directly via the
    session. Round-tripping through the registry endpoints would force
    every test to navigate three flows that aren't under test here."""
    model = ModelArtifact(
        id=uuid7(),
        name="m-exp",
        version=str(uuid4())[:8],
        kind=ModelKind.DETECTION.value,
        backend=ModelBackend.TORCH_LOCAL.value,
        artifact_uri="m-exp/v1/weights.pth",
        status=model_status,
    )
    db_session.add(model)
    dataset = Dataset(
        id=uuid7(),
        name=f"ds-exp-{uuid4().hex[:6]}",
        description="exp e2e",
    )
    db_session.add(dataset)
    await db_session.commit()
    return model, dataset


# ── create ────────────────────────────────────────────────────────────────


async def test_create_experiment_requires_auth(app_client: AsyncClient) -> None:
    r = await app_client.post(
        "/api/v1/experiments",
        json={
            "name": "x",
            "model_id": str(uuid4()),
            "dataset_id": str(uuid4()),
        },
    )
    assert r.status_code == 401


async def test_end_user_is_forbidden_from_creating(
    app_client: AsyncClient, end_user: SeededUser
) -> None:
    r = await app_client.post(
        "/api/v1/experiments",
        headers=auth_header(end_user.token),
        json={
            "name": "x",
            "model_id": str(uuid4()),
            "dataset_id": str(uuid4()),
        },
    )
    assert r.status_code == 403


async def test_ai_dev_can_create_experiment(
    app_client: AsyncClient,
    ai_dev: SeededUser,
    db_session: AsyncSession,
) -> None:
    model, dataset = await _seed_model_and_dataset(db_session)
    r = await app_client.post(
        "/api/v1/experiments",
        headers=auth_header(ai_dev.token),
        json={
            "name": "e2e-ok",
            "model_id": str(model.id),
            "dataset_id": str(dataset.id),
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["data"]["status"] == "pending"
    assert body["data"]["model_id"] == str(model.id)
    assert body["data"]["dataset_id"] == str(dataset.id)


async def test_create_experiment_404_on_missing_model(
    app_client: AsyncClient, ai_dev: SeededUser
) -> None:
    r = await app_client.post(
        "/api/v1/experiments",
        headers=auth_header(ai_dev.token),
        json={
            "name": "x",
            "model_id": str(uuid4()),
            "dataset_id": str(uuid4()),
        },
    )
    assert r.status_code == 404
    assert r.json()["code"] == "not_found"


async def test_create_experiment_422_on_archived_model(
    app_client: AsyncClient,
    ai_dev: SeededUser,
    db_session: AsyncSession,
) -> None:
    model, dataset = await _seed_model_and_dataset(
        db_session, model_status=ModelStatus.ARCHIVED.value
    )
    r = await app_client.post(
        "/api/v1/experiments",
        headers=auth_header(ai_dev.token),
        json={
            "name": "x",
            "model_id": str(model.id),
            "dataset_id": str(dataset.id),
        },
    )
    assert r.status_code == 422
    assert r.json()["code"] == "validation_error"


async def test_create_experiment_404_on_missing_dataset(
    app_client: AsyncClient,
    ai_dev: SeededUser,
    db_session: AsyncSession,
) -> None:
    model, _ = await _seed_model_and_dataset(db_session)
    r = await app_client.post(
        "/api/v1/experiments",
        headers=auth_header(ai_dev.token),
        json={
            "name": "x",
            "model_id": str(model.id),
            "dataset_id": str(uuid4()),
        },
    )
    assert r.status_code == 404


# ── list / detail ─────────────────────────────────────────────────────────


async def test_list_experiments_paginates(
    app_client: AsyncClient,
    ai_dev: SeededUser,
    db_session: AsyncSession,
) -> None:
    model, dataset = await _seed_model_and_dataset(db_session)
    for i in range(3):
        r = await app_client.post(
            "/api/v1/experiments",
            headers=auth_header(ai_dev.token),
            json={
                "name": f"exp-{i}",
                "model_id": str(model.id),
                "dataset_id": str(dataset.id),
            },
        )
        assert r.status_code == 201

    r = await app_client.get(
        "/api/v1/experiments?page=1&page_size=2",
        headers=auth_header(ai_dev.token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["total"] == 3
    assert body["meta"]["page_size"] == 2
    assert body["meta"]["has_more"] is True
    assert len(body["data"]) == 2


async def test_list_experiments_filters_by_model(
    app_client: AsyncClient,
    ai_dev: SeededUser,
    db_session: AsyncSession,
) -> None:
    m1, dataset = await _seed_model_and_dataset(db_session)
    m2, _ = await _seed_model_and_dataset(db_session)
    for m in (m1, m2):
        r = await app_client.post(
            "/api/v1/experiments",
            headers=auth_header(ai_dev.token),
            json={
                "name": f"exp-{m.id}",
                "model_id": str(m.id),
                "dataset_id": str(dataset.id),
            },
        )
        assert r.status_code == 201

    r = await app_client.get(
        f"/api/v1/experiments?model_id={m1.id}",
        headers=auth_header(ai_dev.token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["model_id"] == str(m1.id)


async def test_get_experiment_detail(
    app_client: AsyncClient,
    ai_dev: SeededUser,
    db_session: AsyncSession,
) -> None:
    model, dataset = await _seed_model_and_dataset(db_session)
    r = await app_client.post(
        "/api/v1/experiments",
        headers=auth_header(ai_dev.token),
        json={
            "name": "detail-x",
            "model_id": str(model.id),
            "dataset_id": str(dataset.id),
        },
    )
    assert r.status_code == 201
    exp_id = r.json()["data"]["id"]

    r = await app_client.get(
        f"/api/v1/experiments/{exp_id}",
        headers=auth_header(ai_dev.token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["id"] == exp_id
    assert body["data"]["result_count"] == 0


async def test_get_experiment_404_on_missing(app_client: AsyncClient, ai_dev: SeededUser) -> None:
    r = await app_client.get(
        f"/api/v1/experiments/{uuid4()}",
        headers=auth_header(ai_dev.token),
    )
    assert r.status_code == 404
