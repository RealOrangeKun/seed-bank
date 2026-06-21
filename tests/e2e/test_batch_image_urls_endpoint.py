"""End-to-end coverage for ``GET /api/v1/batches/{id}/image-urls``.

Pins the read-side contract: ``Envelope[list[ImageUrlOut]]`` shape, one
entry per stored image with a non-empty presigned ``url`` and the image
IDs matching the batch's images, ownership scoping (a different
non-admin caller gets 404 — never 403 — so IDs can't be probed), admin
read-any, and 404 on a missing batch.

Submission goes through ``POST /analyze`` with MinIO ``put_object`` and
Celery short-circuited (the worker pipeline is out of scope here, exactly
as in ``test_batches_endpoint.py``). Presigning a GET URL would dial a
real MinIO endpoint, so ``storage_dep`` is overridden with a stub that
returns a deterministic URL — this tier proves the HTTP contract, not the
S3 signature.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient
from PIL import Image

from seedbank.api.deps import storage_dep
from seedbank.infrastructure.db.enums import UserRole
from tests.e2e.conftest import SeedAndLogin, SeededUser, auth_header

pytestmark = pytest.mark.e2e


_STUB_URL = "https://minio.test/presigned-get"


def _png() -> bytes:
    img = Image.new("RGB", (16, 16), color=(120, 200, 80))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class _StubStorage:
    """Deterministic presign so the e2e tier needs no live MinIO.

    Returns a fixed URL with an expiry derived from the requested TTL,
    matching the shape the real :class:`MinioStorage.presigned_get_url`
    produces (a browser-reachable string).
    """

    async def presigned_get_url(self, bucket: str, key: str, ttl: timedelta) -> str:
        return f"{_STUB_URL}?bucket={bucket}&key={key}"


@pytest.fixture(autouse=True)
def _short_circuit_minio_and_celery(monkeypatch: pytest.MonkeyPatch) -> None:
    from seedbank.infrastructure.storage.minio_client import MinioStorage
    from seedbank.workers import celery_app as celery_module

    monkeypatch.setattr(
        MinioStorage, "put_object", AsyncMock(return_value=None)
    )

    def _fake_send_task(*args: Any, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr(
        celery_module.celery_app, "send_task", _fake_send_task
    )


@pytest.fixture
def _stub_storage(app_client: AsyncClient) -> None:
    """Override ``storage_dep`` so ``BatchService`` presigns through the
    stub rather than dialing the (absent) MinIO endpoint.

    Mirrors ``tests/integration/test_models_api.py``: reach into the app
    the ``app_client`` fixture built and swap the dependency, then clean
    up so the override doesn't leak into other tests.
    """
    app = app_client._transport.app  # type: ignore[attr-defined]
    app.dependency_overrides[storage_dep] = lambda: _StubStorage()
    yield
    app.dependency_overrides.pop(storage_dep, None)


async def _submit(client: AsyncClient, token: str, *, n: int = 1) -> str:
    """Submit ``n`` images in one batch, return the batch id."""
    files = [("files", (f"a{i}.png", _png(), "image/png")) for i in range(n)]
    r = await client.post(
        "/api/v1/analyze",
        headers=auth_header(token),
        files=files,
    )
    assert r.status_code == 202, r.text
    return r.json()["data"]["id"]


# ── Happy path ─────────────────────────────────────────────────────────────


async def test_image_urls_returns_envelope_with_one_entry_per_image(
    app_client: AsyncClient, end_user: SeededUser, _stub_storage: None
) -> None:
    batch_id = await _submit(app_client, end_user.token, n=2)

    r = await app_client.get(
        f"/api/v1/batches/{batch_id}/image-urls",
        headers=auth_header(end_user.token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "data" in body
    data = body["data"]
    assert isinstance(data, list)
    assert len(data) == 2
    for entry in data:
        assert set(entry) == {"image_id", "url", "expires_at"}
        assert entry["url"]  # non-empty presigned URL
        # expires_at parses as a future datetime.
        assert datetime.fromisoformat(entry["expires_at"]) > datetime.now(UTC)


async def test_image_urls_image_ids_match_batch_images(
    app_client: AsyncClient, end_user: SeededUser, _stub_storage: None
) -> None:
    batch_id = await _submit(app_client, end_user.token, n=2)

    detail = await app_client.get(
        f"/api/v1/batches/{batch_id}",
        headers=auth_header(end_user.token),
    )
    expected_ids = {img["id"] for img in detail.json()["data"]["images"]}

    r = await app_client.get(
        f"/api/v1/batches/{batch_id}/image-urls",
        headers=auth_header(end_user.token),
    )
    url_ids = {entry["image_id"] for entry in r.json()["data"]}
    assert url_ids == expected_ids


# ── Auth + ownership ───────────────────────────────────────────────────────


async def test_image_urls_unauthenticated_returns_401(
    app_client: AsyncClient, _stub_storage: None
) -> None:
    r = await app_client.get(f"/api/v1/batches/{uuid4()}/image-urls")
    assert r.status_code == 401


async def test_image_urls_for_nonexistent_batch_returns_404_problem(
    app_client: AsyncClient, end_user: SeededUser, _stub_storage: None
) -> None:
    r = await app_client.get(
        f"/api/v1/batches/{uuid4()}/image-urls",
        headers=auth_header(end_user.token),
    )
    assert r.status_code == 404
    assert r.headers.get("content-type", "").startswith(
        "application/problem+json"
    )
    assert r.json()["code"] == "not_found"


async def test_image_urls_owned_by_other_user_returns_404_not_403(
    app_client: AsyncClient,
    seed_and_login: SeedAndLogin,
    _stub_storage: None,
) -> None:
    """Don't leak existence: user B asking for user A's batch images gets
    404, never 403."""
    user_a = await seed_and_login(UserRole.END_USER, email="a@e.com")
    user_b = await seed_and_login(UserRole.END_USER, email="b@e.com")
    batch_id = await _submit(app_client, user_a.token)

    r = await app_client.get(
        f"/api/v1/batches/{batch_id}/image-urls",
        headers=auth_header(user_b.token),
    )
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "not_found"


async def test_admin_can_read_any_batch_image_urls(
    app_client: AsyncClient,
    admin: SeededUser,
    seed_and_login: SeedAndLogin,
    _stub_storage: None,
) -> None:
    user = await seed_and_login(UserRole.END_USER, email="owner@e.com")
    batch_id = await _submit(app_client, user.token)

    r = await app_client.get(
        f"/api/v1/batches/{batch_id}/image-urls",
        headers=auth_header(admin.token),
    )
    assert r.status_code == 200, r.text
    assert len(r.json()["data"]) == 1
