"""HTTP-level tests for ``/api/v1/models``.

Covers RBAC (end_user gets 403) and the ai_developer happy path through
GET / POST / PATCH.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from seedbank.api.deps import storage_dep
from seedbank.core.security import hash_password
from seedbank.infrastructure.db.enums import UserRole
from seedbank.infrastructure.db.models import User
from seedbank.infrastructure.db.repositories import UserRepository

pytestmark = pytest.mark.integration


class _StubStorage:
    """object_exists is the only call the registry service makes."""

    async def object_exists(self, bucket: str, key: str) -> bool:
        return True


async def _seed_user(db_session: AsyncSession, *, email: str, role: UserRole) -> User:
    repo = UserRepository(db_session)
    user = User(
        email=email,
        hashed_password=hash_password("StrongPasswd1A"),
        role=role.value,
        is_active=True,
        is_verified=True,
    )
    await repo.add(user)
    await db_session.commit()
    return user


async def _login(client: AsyncClient, email: str) -> str:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPasswd1A"},
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]["access_token"]


@pytest.fixture
def _override_storage(app_client: AsyncClient) -> None:
    # The fixture creates the app inside its own scope, but exposes the
    # client; we reach into the app to override the storage dep for these
    # tests so the registry's existence check is a no-op.
    app = app_client._transport.app  # type: ignore[attr-defined]
    app.dependency_overrides[storage_dep] = lambda: _StubStorage()
    yield
    app.dependency_overrides.pop(storage_dep, None)


async def test_end_user_cannot_register_model(
    app_client: AsyncClient, db_session: AsyncSession, _override_storage: None
) -> None:
    await _seed_user(db_session, email="end-models@example.com", role=UserRole.END_USER)
    token = await _login(app_client, "end-models@example.com")

    r = await app_client.post(
        "/api/v1/models",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "x",
            "version": "v1",
            "kind": "detection",
            "backend": "torch_local",
            "artifact_uri": "x/v1/weights.pth",
        },
    )
    assert r.status_code == 403


async def test_ai_developer_can_register_and_list(
    app_client: AsyncClient, db_session: AsyncSession, _override_storage: None
) -> None:
    await _seed_user(db_session, email="dev-models@example.com", role=UserRole.AI_DEVELOPER)
    token = await _login(app_client, "dev-models@example.com")
    auth = {"Authorization": f"Bearer {token}"}

    payload = {
        "name": "ai-dev-model",
        "version": "v1",
        "kind": "detection",
        "backend": "torch_local",
        "artifact_uri": "ai-dev-model/v1/weights.pth",
    }
    r = await app_client.post("/api/v1/models", headers=auth, json=payload)
    assert r.status_code == 201, r.text
    created = r.json()["data"]
    assert created["status"] == "registered"
    model_id = created["id"]

    # list filtered by status (paginated envelope)
    r = await app_client.get("/api/v1/models?status=registered", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["total"] >= 1
    assert any(m["id"] == model_id for m in body["data"])

    # promote to staging
    r = await app_client.patch(
        f"/api/v1/models/{model_id}",
        headers=auth,
        json={"status": "staging"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["status"] == "staging"

    # illegal transition: registered already left, can't go back
    r = await app_client.patch(
        f"/api/v1/models/{model_id}",
        headers=auth,
        json={"status": "registered"},
    )
    # ValidationError → 422 in api.errors mapping
    assert r.status_code in (400, 409, 422)


async def test_get_model_404(
    app_client: AsyncClient, db_session: AsyncSession, _override_storage: None
) -> None:
    await _seed_user(db_session, email="dev-404@example.com", role=UserRole.AI_DEVELOPER)
    token = await _login(app_client, "dev-404@example.com")

    r = await app_client.get(
        "/api/v1/models/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
