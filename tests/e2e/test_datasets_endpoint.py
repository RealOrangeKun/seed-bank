"""End-to-end coverage for ``/api/v1/datasets``.

Pins:

* ``ai_developer`` and ``admin`` roles can manage datasets; ``end_user`` is 403.
* Unique-name conflict on duplicate create.
* Bulk-add commits items and ``GET /datasets/{id}/items`` returns them
  paginated.
* Intra-payload duplicate ``image_storage_key`` is rejected.
* Cross-payload duplicate (insert collides with existing row) is rejected.
* 404 Problem on missing dataset.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.e2e.conftest import SeededUser, auth_header

pytestmark = pytest.mark.e2e


def _create_payload(name: str = "ds-1", description: str = "demo") -> dict[str, object]:
    return {"name": name, "description": description}


# ── create ────────────────────────────────────────────────────────────────


async def test_create_dataset_requires_auth(app_client: AsyncClient) -> None:
    r = await app_client.post("/api/v1/datasets", json=_create_payload())
    assert r.status_code == 401


async def test_end_user_is_forbidden_from_creating(
    app_client: AsyncClient, end_user: SeededUser
) -> None:
    r = await app_client.post(
        "/api/v1/datasets",
        headers=auth_header(end_user.token),
        json=_create_payload(),
    )
    assert r.status_code == 403
    assert r.json()["code"] == "forbidden"


async def test_ai_dev_can_create(app_client: AsyncClient, ai_dev: SeededUser) -> None:
    r = await app_client.post(
        "/api/v1/datasets",
        headers=auth_header(ai_dev.token),
        json=_create_payload(name="ds-create-ai"),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["data"]["name"] == "ds-create-ai"
    assert body["data"]["item_count"] == 0


async def test_admin_can_create(app_client: AsyncClient, admin: SeededUser) -> None:
    r = await app_client.post(
        "/api/v1/datasets",
        headers=auth_header(admin.token),
        json=_create_payload(name="ds-create-admin"),
    )
    assert r.status_code == 201


async def test_duplicate_name_conflicts(app_client: AsyncClient, ai_dev: SeededUser) -> None:
    payload = _create_payload(name="dup")
    r1 = await app_client.post("/api/v1/datasets", headers=auth_header(ai_dev.token), json=payload)
    assert r1.status_code == 201, r1.text
    r2 = await app_client.post("/api/v1/datasets", headers=auth_header(ai_dev.token), json=payload)
    assert r2.status_code == 409
    assert r2.json()["code"] == "conflict"


# ── list / detail ─────────────────────────────────────────────────────────


async def test_list_datasets_paginates(app_client: AsyncClient, ai_dev: SeededUser) -> None:
    for i in range(3):
        r = await app_client.post(
            "/api/v1/datasets",
            headers=auth_header(ai_dev.token),
            json=_create_payload(name=f"page-{i}"),
        )
        assert r.status_code == 201

    r = await app_client.get(
        "/api/v1/datasets?page=1&page_size=2",
        headers=auth_header(ai_dev.token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["page"] == 1
    assert body["meta"]["page_size"] == 2
    assert body["meta"]["total"] == 3
    assert body["meta"]["has_more"] is True
    assert len(body["data"]) == 2


async def test_get_dataset_404_problem(app_client: AsyncClient, ai_dev: SeededUser) -> None:
    from uuid import uuid4

    r = await app_client.get(
        f"/api/v1/datasets/{uuid4()}",
        headers=auth_header(ai_dev.token),
    )
    assert r.status_code == 404
    body = r.json()
    assert body["code"] == "not_found"
    assert body["status"] == 404


# ── add_items ─────────────────────────────────────────────────────────────


async def _create_dataset(client: AsyncClient, token: str, name: str) -> str:
    r = await client.post(
        "/api/v1/datasets",
        headers=auth_header(token),
        json={"name": name},
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]["id"]


async def test_add_items_bulk_succeeds(app_client: AsyncClient, ai_dev: SeededUser) -> None:
    ds_id = await _create_dataset(app_client, ai_dev.token, "ds-items")
    r = await app_client.post(
        f"/api/v1/datasets/{ds_id}/items",
        headers=auth_header(ai_dev.token),
        json={
            "items": [
                {
                    "image_storage_key": "ds-items/a.jpg",
                    "ground_truth": {"kind": "classification", "label": "good"},
                },
                {
                    "image_storage_key": "ds-items/b.jpg",
                    "ground_truth": {"kind": "classification", "label": "bad"},
                    "checksum": "deadbeef",
                },
            ]
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["data"]["added"] == 2

    detail = await app_client.get(
        f"/api/v1/datasets/{ds_id}",
        headers=auth_header(ai_dev.token),
    )
    assert detail.status_code == 200
    assert detail.json()["data"]["item_count"] == 2


async def test_add_items_intra_payload_dup_rejected(
    app_client: AsyncClient, ai_dev: SeededUser
) -> None:
    ds_id = await _create_dataset(app_client, ai_dev.token, "ds-intra-dup")
    r = await app_client.post(
        f"/api/v1/datasets/{ds_id}/items",
        headers=auth_header(ai_dev.token),
        json={
            "items": [
                {"image_storage_key": "x"},
                {"image_storage_key": "x"},
            ]
        },
    )
    assert r.status_code == 409
    assert r.json()["code"] == "conflict"


async def test_add_items_cross_payload_dup_rejected(
    app_client: AsyncClient, ai_dev: SeededUser
) -> None:
    ds_id = await _create_dataset(app_client, ai_dev.token, "ds-cross-dup")
    r1 = await app_client.post(
        f"/api/v1/datasets/{ds_id}/items",
        headers=auth_header(ai_dev.token),
        json={"items": [{"image_storage_key": "x"}]},
    )
    assert r1.status_code == 201
    r2 = await app_client.post(
        f"/api/v1/datasets/{ds_id}/items",
        headers=auth_header(ai_dev.token),
        json={"items": [{"image_storage_key": "x"}]},
    )
    assert r2.status_code == 409
    assert r2.json()["code"] == "conflict"


async def test_add_items_to_missing_dataset_404(
    app_client: AsyncClient, ai_dev: SeededUser
) -> None:
    from uuid import uuid4

    r = await app_client.post(
        f"/api/v1/datasets/{uuid4()}/items",
        headers=auth_header(ai_dev.token),
        json={"items": [{"image_storage_key": "x"}]},
    )
    assert r.status_code == 404


async def test_list_items_paginates(app_client: AsyncClient, ai_dev: SeededUser) -> None:
    ds_id = await _create_dataset(app_client, ai_dev.token, "ds-list-items")
    items = [{"image_storage_key": f"img-{i}.jpg"} for i in range(5)]
    r = await app_client.post(
        f"/api/v1/datasets/{ds_id}/items",
        headers=auth_header(ai_dev.token),
        json={"items": items},
    )
    assert r.status_code == 201

    r = await app_client.get(
        f"/api/v1/datasets/{ds_id}/items?page=1&page_size=2",
        headers=auth_header(ai_dev.token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["total"] == 5
    assert body["meta"]["has_more"] is True
    assert len(body["data"]) == 2
