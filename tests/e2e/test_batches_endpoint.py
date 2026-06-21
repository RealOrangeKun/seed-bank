"""End-to-end coverage for ``GET /api/v1/batches`` and ``GET /api/v1/batches/{id}``.

Pins the read-side contract: ``Page[BatchOut]`` envelope on the list,
``Envelope[BatchDetailOut]`` on the detail, ownership scoping (callers
only see their own batches; admin can read any), and 404 Problem Details
on missing/cross-user IDs.

Submission goes through ``POST /analyze`` with MinIO + Celery
short-circuited — the worker pipeline is out of scope here. We only
assert the polling read path.
"""

from __future__ import annotations

import io
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient
from PIL import Image

from seedbank.infrastructure.db.enums import UserRole
from tests.e2e.conftest import SeedAndLogin, SeededUser, auth_header

pytestmark = pytest.mark.e2e


def _png() -> bytes:
    img = Image.new("RGB", (16, 16), color=(120, 200, 80))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def _short_circuit_minio_and_celery(monkeypatch: pytest.MonkeyPatch) -> None:
    from seedbank.infrastructure.storage.minio_client import MinioStorage
    from seedbank.workers import celery_app as celery_module

    monkeypatch.setattr(MinioStorage, "put_object", AsyncMock(return_value=None))

    def _fake_send_task(*args: Any, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr(celery_module.celery_app, "send_task", _fake_send_task)


async def _submit(client: AsyncClient, token: str) -> str:
    """Submit one image, return the batch id from the response."""
    r = await client.post(
        "/api/v1/analyze",
        headers=auth_header(token),
        files=[("files", ("a.png", _png(), "image/png"))],
    )
    assert r.status_code == 202, r.text
    return r.json()["data"]["id"]


# ── List ───────────────────────────────────────────────────────────────────


async def test_list_batches_returns_page_envelope(
    app_client: AsyncClient, end_user: SeededUser
) -> None:
    await _submit(app_client, end_user.token)
    await _submit(app_client, end_user.token)

    r = await app_client.get(
        "/api/v1/batches?page=1&page_size=10",
        headers=auth_header(end_user.token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "data" in body
    assert "meta" in body
    assert body["meta"]["page"] == 1
    assert body["meta"]["page_size"] == 10
    assert body["meta"]["total"] == 2
    assert body["meta"]["has_more"] is False
    assert len(body["data"]) == 2


async def test_list_batches_unauthenticated_returns_401(
    app_client: AsyncClient,
) -> None:
    r = await app_client.get("/api/v1/batches")
    assert r.status_code == 401


async def test_list_batches_pagination_walks_pages(
    app_client: AsyncClient, end_user: SeededUser
) -> None:
    for _ in range(3):
        await _submit(app_client, end_user.token)

    r1 = await app_client.get(
        "/api/v1/batches?page=1&page_size=2",
        headers=auth_header(end_user.token),
    )
    body1 = r1.json()
    assert len(body1["data"]) == 2
    assert body1["meta"]["has_more"] is True

    r2 = await app_client.get(
        "/api/v1/batches?page=2&page_size=2",
        headers=auth_header(end_user.token),
    )
    body2 = r2.json()
    assert len(body2["data"]) == 1
    assert body2["meta"]["has_more"] is False


# ── Ownership scoping ──────────────────────────────────────────────────────


async def test_list_only_returns_caller_batches(
    app_client: AsyncClient,
    seed_and_login: SeedAndLogin,
) -> None:
    user_a = await seed_and_login(UserRole.END_USER, email="a@e.com")
    user_b = await seed_and_login(UserRole.END_USER, email="b@e.com")

    await _submit(app_client, user_a.token)
    await _submit(app_client, user_a.token)
    await _submit(app_client, user_b.token)

    r_a = await app_client.get("/api/v1/batches", headers=auth_header(user_a.token))
    r_b = await app_client.get("/api/v1/batches", headers=auth_header(user_b.token))
    assert r_a.json()["meta"]["total"] == 2
    assert r_b.json()["meta"]["total"] == 1


# ── Detail ─────────────────────────────────────────────────────────────────


async def test_get_batch_returns_envelope_with_nested_graph(
    app_client: AsyncClient, end_user: SeededUser
) -> None:
    batch_id = await _submit(app_client, end_user.token)

    r = await app_client.get(
        f"/api/v1/batches/{batch_id}",
        headers=auth_header(end_user.token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "data" in body
    data = body["data"]
    assert data["id"] == batch_id
    assert data["status"] == "pending"  # worker hasn't run; status frozen
    assert data["image_count"] == 1
    # Nested graph eager-loaded by the service.
    assert isinstance(data.get("images"), list)
    assert len(data["images"]) == 1
    img = data["images"][0]
    # No inferences yet (worker short-circuited) — list stays empty.
    assert img.get("inferences") == []


async def test_get_batch_for_nonexistent_id_returns_404_problem(
    app_client: AsyncClient, end_user: SeededUser
) -> None:
    r = await app_client.get(
        f"/api/v1/batches/{uuid4()}",
        headers=auth_header(end_user.token),
    )
    assert r.status_code == 404
    assert r.headers.get("content-type", "").startswith("application/problem+json")
    assert r.json()["code"] == "not_found"


async def test_get_batch_owned_by_other_user_returns_404_not_403(
    app_client: AsyncClient,
    seed_and_login: SeedAndLogin,
) -> None:
    """Don't leak existence: a batch owned by user A but requested by
    user B comes back as 404, never 403."""
    user_a = await seed_and_login(UserRole.END_USER, email="a@e.com")
    user_b = await seed_and_login(UserRole.END_USER, email="b@e.com")
    batch_id = await _submit(app_client, user_a.token)

    r = await app_client.get(
        f"/api/v1/batches/{batch_id}",
        headers=auth_header(user_b.token),
    )
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "not_found"


async def test_admin_can_read_any_batch(
    app_client: AsyncClient,
    admin: SeededUser,
    seed_and_login: SeedAndLogin,
) -> None:
    user = await seed_and_login(UserRole.END_USER, email="owner@e.com")
    batch_id = await _submit(app_client, user.token)

    r = await app_client.get(
        f"/api/v1/batches/{batch_id}",
        headers=auth_header(admin.token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["id"] == batch_id
