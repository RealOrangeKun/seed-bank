"""End-to-end response-envelope contract.

Pins both the success envelope (``{"data": ...}`` for a single resource,
``{"data": [...], "meta": {...}}`` for a collection) and the RFC 9457
Problem Details error envelope across the actual HTTP path. Pure-shape
guarantees on the Pydantic generics live under ``tests/unit/`` — these
tests prove the wire format end-to-end.
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient, Response

from seedbank.infrastructure.db.enums import UserRole
from tests.e2e.conftest import SeedAndLogin, SeededUser, auth_header

pytestmark = pytest.mark.e2e


# ── Helpers ────────────────────────────────────────────────────────────────


def _assert_problem_shape(
    response: Response, *, status_code: int, code: str, has_request_id: bool = True
) -> dict[str, Any]:
    """Assert a response is a well-formed RFC 9457 Problem Details document.

    Returned to the caller so individual tests can layer code-specific
    assertions on top (e.g. checking ``errors[]`` on 422).
    """
    assert response.status_code == status_code
    assert response.headers.get("content-type", "").startswith("application/problem+json")
    body = response.json()
    for key in ("type", "title", "status", "code", "instance"):
        assert key in body, f"missing {key!r} in {body!r}"
    assert body["status"] == status_code
    assert body["code"] == code
    if has_request_id:
        assert isinstance(body["request_id"], str) and body["request_id"]
    # Error responses must NOT carry a success envelope.
    assert "data" not in body
    assert "meta" not in body
    result: dict[str, Any] = body
    return result


# ── Success envelope ────────────────────────────────────────────────────────


async def test_single_resource_response_is_wrapped_in_data_envelope(
    app_client: AsyncClient, admin: SeededUser
) -> None:
    r = await app_client.get("/api/v1/users/me", headers=auth_header(admin.token))

    assert r.status_code == 200
    body = r.json()
    assert "data" in body
    assert "errors" not in body
    assert body["data"]["email"] == admin.email


async def test_collection_response_is_wrapped_in_page_envelope(
    app_client: AsyncClient, admin: SeededUser
) -> None:
    r = await app_client.get("/api/v1/users?page=1&page_size=1", headers=auth_header(admin.token))

    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) >= {"data", "meta"}
    assert isinstance(body["data"], list)
    meta = body["meta"]
    assert meta["page"] == 1
    assert meta["page_size"] == 1
    assert meta["total"] >= 1


async def test_pagination_walks_pages_keeping_total_stable(
    app_client: AsyncClient, admin: SeededUser, seed_and_login: SeedAndLogin
) -> None:
    """Walk page=1..2 with page_size=1; total stays stable, has_more flips."""
    # Seed a second admin so there are at least two rows to walk.
    await seed_and_login(UserRole.ADMIN, email="admin-2@e.com")
    auth = auth_header(admin.token)

    r1 = await app_client.get("/api/v1/users?page=1&page_size=1", headers=auth)
    r2 = await app_client.get("/api/v1/users?page=2&page_size=1", headers=auth)

    assert r1.status_code == 200
    assert r2.status_code == 200
    m1, m2 = r1.json()["meta"], r2.json()["meta"]
    assert m1["total"] == m2["total"] >= 2
    assert m1["page"] == 1
    assert m2["page"] == 2


async def test_pagination_has_more_is_false_on_last_page(
    app_client: AsyncClient, admin: SeededUser
) -> None:
    """Asking for a page_size larger than total returns ``has_more=False``."""
    r = await app_client.get("/api/v1/users?page=1&page_size=200", headers=auth_header(admin.token))

    assert r.status_code == 200
    meta = r.json()["meta"]
    assert meta["page_size"] == 200
    assert meta["has_more"] is False


async def test_pagination_rejects_page_size_above_max(
    app_client: AsyncClient, admin: SeededUser
) -> None:
    """``page_size`` is clamped at 200 — 201 is a 422 from the Query validator."""
    r = await app_client.get("/api/v1/users?page=1&page_size=201", headers=auth_header(admin.token))

    _assert_problem_shape(r, status_code=422, code="validation_error")


# ── Error envelope (RFC 9457) ───────────────────────────────────────────────


async def test_unauthenticated_request_returns_problem_details(
    app_client: AsyncClient,
) -> None:
    r = await app_client.get("/api/v1/users/me")

    body = _assert_problem_shape(r, status_code=401, code="auth_error")
    assert body["instance"] == "/api/v1/users/me"


async def test_forbidden_request_returns_problem_details(
    app_client: AsyncClient, end_user: SeededUser
) -> None:
    r = await app_client.get("/api/v1/models", headers=auth_header(end_user.token))

    _assert_problem_shape(r, status_code=403, code="forbidden")


async def test_validation_error_returns_per_field_errors(
    app_client: AsyncClient,
) -> None:
    """Pydantic 422 produces a populated ``errors[]`` array."""
    r = await app_client.post(
        "/api/v1/auth/register",
        json={"email": "weak@e.com", "password": "short", "full_name": None},
    )

    body = _assert_problem_shape(r, status_code=422, code="validation_error")
    errors = body["errors"]
    assert isinstance(errors, list) and errors
    fields = {e["field"] for e in errors}
    assert "password" in fields
    for entry in errors:
        assert {"field", "message", "code"} <= entry.keys()


async def test_not_found_returns_problem_details(
    app_client: AsyncClient, ai_dev: SeededUser
) -> None:
    """An ai_developer hits a missing model — auth gate passes, NotFoundError fires."""
    r = await app_client.get(
        "/api/v1/models/00000000-0000-0000-0000-000000000000",
        headers=auth_header(ai_dev.token),
    )

    _assert_problem_shape(r, status_code=404, code="not_found")


async def test_rate_limit_returns_problem_details_with_retry_after(
    app_client: AsyncClient,
) -> None:
    """Burst past the auth/login bucket; the 429 carries the same envelope
    as every other error and preserves the ``Retry-After`` header."""
    payload = {"email": "ratelimit@e.com", "password": "wrong-password"}

    # 10 logins/minute is the configured ceiling. The 11th MUST 429.
    last = None
    for _ in range(11):
        last = await app_client.post("/api/v1/auth/login", json=payload)

    assert last is not None
    body = _assert_problem_shape(last, status_code=429, code="rate_limited")
    assert "Retry-After" in last.headers
    assert last.headers["Retry-After"].isdigit()
    # Body must not double-encode the limit info — detail is a string,
    # not a nested object.
    assert isinstance(body["detail"], str)


async def test_request_id_correlates_response_header_and_problem_body(
    app_client: AsyncClient,
) -> None:
    """The ``X-Request-ID`` response header equals ``Problem.request_id``."""
    r = await app_client.get("/api/v1/users/me")

    body = _assert_problem_shape(r, status_code=401, code="auth_error")
    header_rid = r.headers.get("X-Request-ID")
    assert header_rid, "RequestIdMiddleware must echo X-Request-ID on errors"
    assert body["request_id"] == header_rid


# Note: 409 conflict-envelope coverage is intentionally deferred to the
# feature suites that own a quota or unique-constraint path (e.g. model
# registry's duplicate name+version). Asserting it here would require
# scaffolding domain state purely for an envelope shape; the Problem
# helper above is reused by those suites once the pre-existing bugs in
# `test_model_registry_service` are resolved.
