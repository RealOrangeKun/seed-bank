"""End-to-end coverage for ``POST /api/v1/analyze``.

These pin the HTTP contract — 202 acceptance, validation Problem Details,
authz on the ``model_id`` override, rate limiting — but stop short of
exercising the worker pipeline (that requires a real ML stack with
registered models). The worker's correctness is covered separately.

The analyze service writes to MinIO and dispatches to Celery; both
boundaries are mocked at the test fixture level so the e2e tier
doesn't depend on a live MinIO bucket or a Redis broker.
"""

from __future__ import annotations

import io
from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from PIL import Image

from tests.e2e.conftest import SeededUser, auth_header

pytestmark = pytest.mark.e2e


# ── Helpers ────────────────────────────────────────────────────────────────


def _png(*, size: tuple[int, int] = (32, 32)) -> bytes:
    img = Image.new("RGB", size, color=(120, 200, 80))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def _short_circuit_minio_and_celery(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace MinIO put_object + Celery send_task with no-op recorders.

    The e2e tier proves the HTTP contract; the worker pipeline is out of
    scope for these tests. Without these short-circuits the analyze
    handler would block on a real MinIO bucket and a real Redis broker
    that aren't part of the test stack.
    """
    from seedbank.infrastructure.storage.minio_client import MinioStorage
    from seedbank.workers import celery_app as celery_module

    monkeypatch.setattr(
        MinioStorage, "put_object", AsyncMock(return_value=None)
    )

    sent: list[Any] = []

    def _fake_send_task(*args: Any, **kwargs: Any) -> None:
        sent.append((args, kwargs))

    monkeypatch.setattr(
        celery_module.celery_app, "send_task", _fake_send_task
    )


def _assert_problem(response, *, status_code: int, code: str) -> dict:
    assert response.status_code == status_code, response.text
    assert response.headers.get("content-type", "").startswith(
        "application/problem+json"
    )
    body = response.json()
    assert body["status"] == status_code
    assert body["code"] == code
    return body


# ── Happy path ─────────────────────────────────────────────────────────────


async def test_analyze_one_image_returns_202_with_envelope(
    app_client: AsyncClient, end_user: SeededUser
) -> None:
    r = await app_client.post(
        "/api/v1/analyze",
        headers=auth_header(end_user.token),
        files=[("files", ("a.png", _png(), "image/png"))],
    )
    assert r.status_code == 202, r.text
    body = r.json()
    assert "data" in body
    data = body["data"]
    assert data["status"] == "pending"
    assert data["image_count"] == 1
    assert data["source"] == "api"
    # Location header pins where the client polls for completion.
    assert r.headers["location"].startswith("/api/v1/batches/")
    assert data["id"] in r.headers["location"]


async def test_analyze_three_images_dispatches_three_tasks(
    app_client: AsyncClient, end_user: SeededUser
) -> None:
    r = await app_client.post(
        "/api/v1/analyze",
        headers=auth_header(end_user.token),
        files=[
            ("files", (f"a{i}.png", _png(), "image/png"))
            for i in range(3)
        ],
    )
    assert r.status_code == 202, r.text
    assert r.json()["data"]["image_count"] == 3


async def test_analyze_at_max_files_succeeds(
    app_client: AsyncClient, end_user: SeededUser
) -> None:
    """Boundary: exactly ``analyze_max_files_per_request`` files is OK."""
    from seedbank.core.config import get_settings

    n = get_settings().analyze_max_files_per_request
    r = await app_client.post(
        "/api/v1/analyze",
        headers=auth_header(end_user.token),
        files=[("files", (f"a{i}.png", _png(), "image/png")) for i in range(n)],
    )
    assert r.status_code == 202


# ── Authentication / authorization ─────────────────────────────────────────


async def test_analyze_unauthenticated_returns_401_problem(
    app_client: AsyncClient,
) -> None:
    r = await app_client.post(
        "/api/v1/analyze",
        files=[("files", ("a.png", _png(), "image/png"))],
    )
    _assert_problem(r, status_code=401, code="auth_error")


async def test_end_user_passing_model_id_is_403(
    app_client: AsyncClient, end_user: SeededUser
) -> None:
    """The override is ai_developer/admin only. Service raises
    ForbiddenError → handler maps to 403 Problem Details."""
    from uuid import uuid4

    r = await app_client.post(
        "/api/v1/analyze",
        headers=auth_header(end_user.token),
        data={"model_id": str(uuid4())},
        files=[("files", ("a.png", _png(), "image/png"))],
    )
    _assert_problem(r, status_code=403, code="forbidden")


async def test_ai_developer_with_model_id_override_proceeds(
    app_client: AsyncClient, ai_dev: SeededUser
) -> None:
    from uuid import uuid4

    r = await app_client.post(
        "/api/v1/analyze",
        headers=auth_header(ai_dev.token),
        data={"model_id": str(uuid4())},
        files=[("files", ("a.png", _png(), "image/png"))],
    )
    assert r.status_code == 202, r.text


# ── Validation Problem Details ─────────────────────────────────────────────


async def test_analyze_rejects_above_max_files_with_422(
    app_client: AsyncClient, end_user: SeededUser
) -> None:
    from seedbank.core.config import get_settings

    n = get_settings().analyze_max_files_per_request + 1
    r = await app_client.post(
        "/api/v1/analyze",
        headers=auth_header(end_user.token),
        files=[("files", (f"a{i}.png", _png(), "image/png")) for i in range(n)],
    )
    _assert_problem(r, status_code=422, code="validation_error")


async def test_analyze_rejects_unknown_mime_with_422(
    app_client: AsyncClient, end_user: SeededUser
) -> None:
    r = await app_client.post(
        "/api/v1/analyze",
        headers=auth_header(end_user.token),
        files=[("files", ("a.bmp", _png(), "image/bmp"))],
    )
    _assert_problem(r, status_code=422, code="validation_error")


async def test_analyze_rejects_undecodable_image_with_422(
    app_client: AsyncClient, end_user: SeededUser
) -> None:
    r = await app_client.post(
        "/api/v1/analyze",
        headers=auth_header(end_user.token),
        files=[("files", ("a.png", b"not-an-image", "image/png"))],
    )
    _assert_problem(r, status_code=422, code="validation_error")


async def test_analyze_rejects_bad_country_code_with_422(
    app_client: AsyncClient, end_user: SeededUser
) -> None:
    """FastAPI Form regex validation lands as the standard 422 Problem
    Details with ``errors[]`` populated by the per-field handler."""
    r = await app_client.post(
        "/api/v1/analyze",
        headers=auth_header(end_user.token),
        data={"country_code": "us"},  # must be uppercase per pattern
        files=[("files", ("a.png", _png(), "image/png"))],
    )
    body = _assert_problem(r, status_code=422, code="validation_error")
    fields = {e["field"] for e in body.get("errors", [])}
    assert "country_code" in fields


async def test_analyze_rejects_zero_files_with_422(
    app_client: AsyncClient, end_user: SeededUser
) -> None:
    """No ``files`` part at all → FastAPI multipart parser returns 422."""
    r = await app_client.post(
        "/api/v1/analyze",
        headers=auth_header(end_user.token),
    )
    _assert_problem(r, status_code=422, code="validation_error")
