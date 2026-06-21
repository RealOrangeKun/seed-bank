"""End-to-end coverage for ``POST /api/v1/auth/bootstrap-admin``.

The endpoint exists to break the chicken-and-egg in fresh deployments:
nobody can promote you to admin if no admin exists. These tests pin the
gate logic at the HTTP boundary — token presence, idempotence, validation,
and the success envelope.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.e2e.conftest import TEST_BOOTSTRAP_TOKEN, auth_header
from tests.factories import DEFAULT_TEST_PASSWORD

pytestmark = pytest.mark.e2e


def _payload(**overrides: object) -> dict:
    base = {
        "email": "root@e.com",
        "password": DEFAULT_TEST_PASSWORD,
        "full_name": "Root Admin",
        "bootstrap_token": TEST_BOOTSTRAP_TOKEN,
    }
    base.update(overrides)
    return base


# ── Happy path ─────────────────────────────────────────────────────────────


async def test_bootstrap_admin_creates_first_admin(
    app_client: AsyncClient,
) -> None:
    r = await app_client.post("/api/v1/auth/bootstrap-admin", json=_payload())

    assert r.status_code == 201, r.text
    body = r.json()
    assert "data" in body
    assert body["data"]["email"] == "root@e.com"
    assert body["data"]["role"] == "admin"


async def test_bootstrapped_admin_can_immediately_login(
    app_client: AsyncClient,
) -> None:
    """The new admin is created with ``is_verified=True`` so they can log
    in without going through email verification."""
    r = await app_client.post("/api/v1/auth/bootstrap-admin", json=_payload())
    assert r.status_code == 201

    login = await app_client.post(
        "/api/v1/auth/login",
        json={"email": "root@e.com", "password": DEFAULT_TEST_PASSWORD},
    )
    assert login.status_code == 200, login.text
    token = login.json()["data"]["access_token"]

    me = await app_client.get("/api/v1/users/me", headers=auth_header(token))
    assert me.status_code == 200
    assert me.json()["data"]["role"] == "admin"


# ── Rejection paths (RFC 9457 Problem Details) ─────────────────────────────


async def test_bootstrap_rejects_wrong_token_with_401(
    app_client: AsyncClient,
) -> None:
    r = await app_client.post(
        "/api/v1/auth/bootstrap-admin",
        json=_payload(bootstrap_token="not-the-real-token"),
    )

    assert r.status_code == 401
    assert r.headers.get("content-type", "").startswith("application/problem+json")
    body = r.json()
    assert body["code"] == "auth_error"


async def test_bootstrap_is_idempotent_returns_409_when_admin_exists(
    app_client: AsyncClient,
) -> None:
    """Calling the endpoint twice produces exactly one admin: the second
    call hits ``ConflictError`` regardless of which email/password it
    presents. This is the production safety net — even if the token leaks
    later, the attacker cannot mint a second admin."""
    first = await app_client.post("/api/v1/auth/bootstrap-admin", json=_payload())
    assert first.status_code == 201

    second = await app_client.post(
        "/api/v1/auth/bootstrap-admin",
        json=_payload(email="other@e.com"),
    )

    assert second.status_code == 409
    body = second.json()
    assert body["code"] == "conflict"


async def test_bootstrap_rejects_weak_password_with_422(
    app_client: AsyncClient,
) -> None:
    r = await app_client.post(
        "/api/v1/auth/bootstrap-admin",
        json=_payload(password="short"),
    )

    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "validation_error"
    fields = {e["field"] for e in body["errors"]}
    assert "password" in fields


async def test_bootstrap_rejects_invalid_email_with_422(
    app_client: AsyncClient,
) -> None:
    r = await app_client.post(
        "/api/v1/auth/bootstrap-admin",
        json=_payload(email="not-an-email"),
    )

    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "validation_error"


async def test_bootstrap_rejects_extra_fields_with_422(
    app_client: AsyncClient,
) -> None:
    """``model_config = ConfigDict(extra="forbid")`` on ``BootstrapAdminIn``
    means a typo'd field (e.g. ``role: "ai_developer"`` hoping to bootstrap
    a non-admin role) is rejected, not silently ignored."""
    r = await app_client.post(
        "/api/v1/auth/bootstrap-admin",
        json={**_payload(), "role": "ai_developer"},
    )

    assert r.status_code == 422
