"""End-to-end coverage for ``/api/v1/catalog`` — seed types + suppliers.

Pins:

* ``GET /seed-types`` lists the catalog for any authenticated actor.
* Supplier CRUD happy path (create private → list → patch → delete).
* RBAC: ``end_user`` is 403 on ``POST /suppliers``; reads are open to
  any authenticated actor; unauthenticated is 401.
* Global suppliers are admin-only to create; ``ai_developer`` gets 403.
* Per-resource authz: a user can't mutate another user's private supplier.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from seedbank.bootstrap import bootstrap_seed_types
from seedbank.bootstrap.seed_types import SeedTypeSpec
from seedbank.infrastructure.db.enums import UserRole
from tests.e2e.conftest import SeedAndLogin, SeededUser, auth_header

pytestmark = pytest.mark.e2e


# ── seed types ──────────────────────────────────────────────────────────────


async def test_seed_types_requires_auth(app_client: AsyncClient) -> None:
    r = await app_client.get("/api/v1/seed-types")
    assert r.status_code == 401


async def test_list_seed_types_returns_catalog(
    app_client: AsyncClient, db_session: AsyncSession, end_user: SeededUser
) -> None:
    await bootstrap_seed_types(
        db_session,
        [
            SeedTypeSpec(code="coffee", display_name="Coffee"),
            SeedTypeSpec(code="maize", display_name="Maize"),
        ],
    )
    await db_session.commit()

    r = await app_client.get("/api/v1/seed-types", headers=auth_header(end_user.token))
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    codes = {row["code"] for row in data}
    assert {"coffee", "maize"} <= codes


# ── suppliers: RBAC ─────────────────────────────────────────────────────────


async def test_end_user_can_read_but_not_create_suppliers(
    app_client: AsyncClient, end_user: SeededUser
) -> None:
    r_read = await app_client.get("/api/v1/suppliers", headers=auth_header(end_user.token))
    assert r_read.status_code == 200, r_read.text

    r_create = await app_client.post(
        "/api/v1/suppliers",
        headers=auth_header(end_user.token),
        json={"name": "End User Co"},
    )
    assert r_create.status_code == 403
    assert r_create.json()["code"] == "forbidden"


async def test_create_supplier_requires_auth(app_client: AsyncClient) -> None:
    r = await app_client.post("/api/v1/suppliers", json={"name": "x"})
    assert r.status_code == 401


# ── suppliers: CRUD happy path ──────────────────────────────────────────────


async def test_supplier_crud_happy_path(app_client: AsyncClient, ai_dev: SeededUser) -> None:
    # create (private)
    r = await app_client.post(
        "/api/v1/suppliers",
        headers=auth_header(ai_dev.token),
        json={"name": "Acme Local", "metadata": {"region": "EA"}},
    )
    assert r.status_code == 201, r.text
    created = r.json()["data"]
    assert created["is_global"] is False
    assert created["is_active"] is True
    assert created["metadata"] == {"region": "EA"}
    supplier_id = created["id"]

    # list shows it
    r_list = await app_client.get("/api/v1/suppliers", headers=auth_header(ai_dev.token))
    assert r_list.status_code == 200
    assert any(s["id"] == supplier_id for s in r_list.json()["data"])

    # patch
    r_patch = await app_client.patch(
        f"/api/v1/suppliers/{supplier_id}",
        headers=auth_header(ai_dev.token),
        json={"name": "Acme Renamed", "is_active": False},
    )
    assert r_patch.status_code == 200, r_patch.text
    patched = r_patch.json()["data"]
    assert patched["name"] == "Acme Renamed"
    assert patched["is_active"] is False

    # delete (204, no body)
    r_del = await app_client.delete(
        f"/api/v1/suppliers/{supplier_id}",
        headers=auth_header(ai_dev.token),
    )
    assert r_del.status_code == 204
    assert r_del.content == b""

    # gone from the list (an inactive row was never listed; deleted stays out)
    r_list2 = await app_client.get("/api/v1/suppliers", headers=auth_header(ai_dev.token))
    assert all(s["id"] != supplier_id for s in r_list2.json()["data"])


async def test_ai_dev_cannot_create_global_supplier(
    app_client: AsyncClient, ai_dev: SeededUser
) -> None:
    r = await app_client.post(
        "/api/v1/suppliers",
        headers=auth_header(ai_dev.token),
        json={"name": "Big Global", "is_global": True},
    )
    assert r.status_code == 403
    assert r.json()["code"] == "forbidden"


async def test_admin_can_create_global_supplier(app_client: AsyncClient, admin: SeededUser) -> None:
    r = await app_client.post(
        "/api/v1/suppliers",
        headers=auth_header(admin.token),
        json={"name": "Global Seeds", "is_global": True},
    )
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    assert data["is_global"] is True
    assert data["created_by_user_id"] is None


async def test_user_cannot_patch_another_users_private_supplier(
    app_client: AsyncClient, seed_and_login: SeedAndLogin
) -> None:
    owner = await seed_and_login(UserRole.AI_DEVELOPER, email="owner@e.com")
    other = await seed_and_login(UserRole.AI_DEVELOPER, email="other@e.com")

    r = await app_client.post(
        "/api/v1/suppliers",
        headers=auth_header(owner.token),
        json={"name": "Owner Private"},
    )
    assert r.status_code == 201, r.text
    supplier_id = r.json()["data"]["id"]

    # ``other`` can't see it (private to owner) → 404, never 403, so the
    # other user can't probe for its existence.
    r_patch = await app_client.patch(
        f"/api/v1/suppliers/{supplier_id}",
        headers=auth_header(other.token),
        json={"name": "Hijacked"},
    )
    assert r_patch.status_code == 404
    assert r_patch.json()["code"] == "not_found"


async def test_patch_missing_supplier_404(app_client: AsyncClient, ai_dev: SeededUser) -> None:
    r = await app_client.patch(
        f"/api/v1/suppliers/{uuid4()}",
        headers=auth_header(ai_dev.token),
        json={"name": "x"},
    )
    assert r.status_code == 404
    assert r.json()["code"] == "not_found"


async def test_ai_dev_cannot_modify_global_supplier(
    app_client: AsyncClient, admin: SeededUser, ai_dev: SeededUser
) -> None:
    r = await app_client.post(
        "/api/v1/suppliers",
        headers=auth_header(admin.token),
        json={"name": "Curated Global", "is_global": True},
    )
    assert r.status_code == 201, r.text
    supplier_id = r.json()["data"]["id"]

    r_patch = await app_client.patch(
        f"/api/v1/suppliers/{supplier_id}",
        headers=auth_header(ai_dev.token),
        json={"is_active": False},
    )
    assert r_patch.status_code == 403
    assert r_patch.json()["code"] == "forbidden"
