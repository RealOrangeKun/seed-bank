"""Unit tests for :class:`seedbank.services.catalog_service.CatalogService`.

Focus is the supplier authorization matrix the router delegates to the
service — there is no transport here, so the rules are pinned directly:

* non-admin creating a global supplier → ``ForbiddenError``
* non-owner mutating a private supplier → ``ForbiddenError``
* non-admin mutating a global supplier → ``ForbiddenError``
* owner / admin happy paths commit
* missing/invisible supplier → ``NotFoundError``
* IntegrityError on create → ``ConflictError``
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from seedbank.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from seedbank.domain.user import AuthenticatedUser, Role
from seedbank.infrastructure.db.models import Supplier
from seedbank.services.catalog_service import CatalogService

pytestmark = pytest.mark.unit


def _make_actor(role: Role = Role.AI_DEVELOPER, *, user_id: Any = None) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=user_id or uuid4(),
        email="actor@dev.com",
        role=role,
        is_active=True,
        is_verified=True,
        scopes=frozenset(),
        auth_method="jwt",
    )


class _FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def flush(self) -> None:
        pass

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def refresh(self, instance: object) -> None:
        # No-op: the fake doesn't model DB-side defaults. The service calls
        # refresh() after commit so created_at/updated_at load before the
        # router serialises SupplierOut (see catalog_service).
        pass


def _build_service() -> tuple[CatalogService, _FakeSession, MagicMock, MagicMock]:
    session = _FakeSession()
    seed_types = MagicMock()
    seed_types.list_all = AsyncMock(return_value=[])
    suppliers = MagicMock()
    suppliers.list_visible_to = AsyncMock(return_value=[])
    suppliers.get_visible = AsyncMock(return_value=None)
    suppliers.add = AsyncMock(side_effect=lambda x: x)
    svc = CatalogService(
        session=session,  # type: ignore[arg-type]
        seed_types=seed_types,
        suppliers=suppliers,
    )
    return svc, session, seed_types, suppliers


def _private_supplier(owner_id: Any) -> Supplier:
    return Supplier(
        id=uuid4(),
        name="Private Co",
        slug="private-co-deadbeef",
        is_global=False,
        created_by_user_id=owner_id,
        is_active=True,
    )


def _global_supplier() -> Supplier:
    return Supplier(
        id=uuid4(),
        name="Global Co",
        slug="global-co",
        is_global=True,
        created_by_user_id=None,
        is_active=True,
    )


# ── create ──────────────────────────────────────────────────────────────────


async def test_non_admin_cannot_create_global_supplier() -> None:
    svc, session, _seed, suppliers = _build_service()

    with pytest.raises(ForbiddenError):
        await svc.create_supplier(
            actor=_make_actor(Role.AI_DEVELOPER),
            name="Big Seeds",
            is_global=True,
            metadata=None,
        )
    suppliers.add.assert_not_awaited()
    assert session.commits == 0


async def test_admin_can_create_global_supplier() -> None:
    svc, session, _seed, suppliers = _build_service()

    out = await svc.create_supplier(
        actor=_make_actor(Role.ADMIN),
        name="Big Seeds",
        is_global=True,
        metadata={"region": "EA"},
    )
    suppliers.add.assert_awaited_once()
    assert session.commits == 1
    assert out.is_global is True
    assert out.created_by_user_id is None
    assert out.slug.startswith("big-seeds-")


async def test_private_supplier_is_owned_by_actor() -> None:
    svc, session, _seed, _suppliers = _build_service()
    actor = _make_actor(Role.AI_DEVELOPER)

    out = await svc.create_supplier(
        actor=actor,
        name="My Local Co",
        is_global=False,
        metadata=None,
    )
    assert out.is_global is False
    assert out.created_by_user_id == actor.id
    assert session.commits == 1


async def test_create_translates_integrity_error_to_conflict() -> None:
    svc, session, _seed, suppliers = _build_service()
    suppliers.add = AsyncMock(side_effect=IntegrityError("x", {}, Exception("uq")))

    with pytest.raises(ConflictError):
        await svc.create_supplier(
            actor=_make_actor(Role.AI_DEVELOPER),
            name="Dup Co",
            is_global=False,
            metadata=None,
        )
    assert session.rollbacks == 1


# ── update / delete authz ─────────────────────────────────────────────────


async def test_update_missing_supplier_raises_not_found() -> None:
    svc, _session, _seed, suppliers = _build_service()
    suppliers.get_visible = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError):
        await svc.update_supplier(
            actor=_make_actor(),
            supplier_id=uuid4(),
            name="x",
            is_active=None,
            metadata=None,
        )


async def test_non_owner_cannot_update_private_supplier() -> None:
    svc, _session, _seed, suppliers = _build_service()
    suppliers.get_visible = AsyncMock(return_value=_private_supplier(uuid4()))

    with pytest.raises(ForbiddenError):
        await svc.update_supplier(
            actor=_make_actor(Role.AI_DEVELOPER),  # different id
            supplier_id=uuid4(),
            name="x",
            is_active=None,
            metadata=None,
        )


async def test_non_admin_cannot_update_global_supplier() -> None:
    svc, _session, _seed, suppliers = _build_service()
    suppliers.get_visible = AsyncMock(return_value=_global_supplier())

    with pytest.raises(ForbiddenError):
        await svc.update_supplier(
            actor=_make_actor(Role.AI_DEVELOPER),
            supplier_id=uuid4(),
            name="x",
            is_active=None,
            metadata=None,
        )


async def test_owner_can_update_private_supplier() -> None:
    svc, session, _seed, suppliers = _build_service()
    owner_id = uuid4()
    supplier = _private_supplier(owner_id)
    suppliers.get_visible = AsyncMock(return_value=supplier)

    out = await svc.update_supplier(
        actor=_make_actor(Role.AI_DEVELOPER, user_id=owner_id),
        supplier_id=supplier.id,
        name="Renamed Co",
        is_active=False,
        metadata={"k": "v"},
    )
    assert out.name == "Renamed Co"
    assert out.is_active is False
    assert out.supplier_metadata == {"k": "v"}
    assert session.commits == 1


async def test_admin_can_update_global_supplier() -> None:
    svc, session, _seed, suppliers = _build_service()
    supplier = _global_supplier()
    suppliers.get_visible = AsyncMock(return_value=supplier)

    out = await svc.update_supplier(
        actor=_make_actor(Role.ADMIN),
        supplier_id=supplier.id,
        name=None,
        is_active=False,
        metadata=None,
    )
    assert out.is_active is False
    assert out.name == "Global Co"  # name left untouched (None not applied)
    assert session.commits == 1


async def test_soft_delete_stamps_deleted_at_for_owner() -> None:
    svc, session, _seed, suppliers = _build_service()
    owner_id = uuid4()
    supplier = _private_supplier(owner_id)
    suppliers.get_visible = AsyncMock(return_value=supplier)

    await svc.soft_delete_supplier(
        actor=_make_actor(Role.AI_DEVELOPER, user_id=owner_id),
        supplier_id=supplier.id,
    )
    assert supplier.deleted_at is not None
    assert session.commits == 1


async def test_non_owner_cannot_soft_delete_private_supplier() -> None:
    svc, session, _seed, suppliers = _build_service()
    suppliers.get_visible = AsyncMock(return_value=_private_supplier(uuid4()))

    with pytest.raises(ForbiddenError):
        await svc.soft_delete_supplier(
            actor=_make_actor(Role.AI_DEVELOPER),
            supplier_id=uuid4(),
        )
    assert session.commits == 0
