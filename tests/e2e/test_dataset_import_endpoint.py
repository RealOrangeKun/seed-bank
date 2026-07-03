"""End-to-end coverage for ``POST /api/v1/datasets/{id}/import``.

Pins the dispatch surface only — RBAC, the 202 acknowledgement, the 404 on a
missing dataset, and the 422 when the referenced archive isn't in storage. The
Celery ``send_task`` is short-circuited (the unpack worker is exercised
against the live stack in verification; its pure extraction logic is covered by
``tests/unit/test_dataset_import.py``). ``MinioStorage.object_exists`` is
stubbed so the test never dials a real MinIO.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.e2e.conftest import SeededUser, auth_header

pytestmark = pytest.mark.e2e


@pytest.fixture(autouse=True)
def _capture_celery(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Short-circuit dispatch and record the calls for assertions."""
    from seedbank.workers import celery_app as celery_module

    calls: list[dict[str, Any]] = []

    def _fake_send_task(name: str, *args: Any, **kwargs: Any) -> None:
        calls.append({"name": name, "kwargs": kwargs})
        return

    monkeypatch.setattr(celery_module.celery_app, "send_task", _fake_send_task)
    return calls


def _stub_object_exists(monkeypatch: pytest.MonkeyPatch, *, exists: bool) -> None:
    from seedbank.infrastructure.storage.minio_client import MinioStorage

    async def _fake(self: MinioStorage, bucket: str, key: str) -> bool:
        return exists

    monkeypatch.setattr(MinioStorage, "object_exists", _fake)


async def _create_dataset(client: AsyncClient, token: str, name: str) -> str:
    r = await client.post("/api/v1/datasets", headers=auth_header(token), json={"name": name})
    assert r.status_code == 201, r.text
    dataset_id: str = r.json()["data"]["id"]
    return dataset_id


async def test_import_requires_auth(app_client: AsyncClient) -> None:
    r = await app_client.post(
        f"/api/v1/datasets/{uuid4()}/import",
        json={"zip_storage_key": "datasets/x/y.zip"},
    )
    assert r.status_code == 401


async def test_end_user_is_forbidden(app_client: AsyncClient, end_user: SeededUser) -> None:
    r = await app_client.post(
        f"/api/v1/datasets/{uuid4()}/import",
        headers=auth_header(end_user.token),
        json={"zip_storage_key": "datasets/x/y.zip"},
    )
    assert r.status_code == 403


async def test_import_missing_dataset_404(
    app_client: AsyncClient, ai_dev: SeededUser, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_object_exists(monkeypatch, exists=True)
    r = await app_client.post(
        f"/api/v1/datasets/{uuid4()}/import",
        headers=auth_header(ai_dev.token),
        json={"zip_storage_key": "datasets/x/y.zip"},
    )
    assert r.status_code == 404
    assert r.json()["code"] == "not_found"


async def test_import_missing_archive_422(
    app_client: AsyncClient, ai_dev: SeededUser, monkeypatch: pytest.MonkeyPatch
) -> None:
    ds_id = await _create_dataset(app_client, ai_dev.token, "ds-import-noarchive")
    _stub_object_exists(monkeypatch, exists=False)
    r = await app_client.post(
        f"/api/v1/datasets/{ds_id}/import",
        headers=auth_header(ai_dev.token),
        json={"zip_storage_key": "datasets/x/missing.zip"},
    )
    assert r.status_code == 422
    assert r.json()["code"] == "validation_error"


async def test_import_dispatches_task(
    app_client: AsyncClient,
    ai_dev: SeededUser,
    monkeypatch: pytest.MonkeyPatch,
    _capture_celery: list[dict[str, Any]],
) -> None:
    ds_id = await _create_dataset(app_client, ai_dev.token, "ds-import-ok")
    _stub_object_exists(monkeypatch, exists=True)
    r = await app_client.post(
        f"/api/v1/datasets/{ds_id}/import",
        headers=auth_header(ai_dev.token),
        json={"zip_storage_key": f"datasets/{ds_id}/upload.zip"},
    )
    assert r.status_code == 202, r.text
    assert r.json()["data"]["dispatched"] is True
    assert any(c["name"] == "seedbank.import_yolo_dataset" for c in _capture_celery)
    dispatched = next(c for c in _capture_celery if c["name"] == "seedbank.import_yolo_dataset")
    assert dispatched["kwargs"].get("queue") == "default"
