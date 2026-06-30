"""Unit tests for :class:`seedbank.services.dataset_service.DatasetService`.

Covers:

* unique-name conflict on create
* dataset-not-found on get / add_items / list_items
* intra-payload duplicate detection in ``add_items``
* IntegrityError translation to ``ConflictError``
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from seedbank.core.exceptions import ConflictError, NotFoundError
from seedbank.domain.user import AuthenticatedUser, Role
from seedbank.schemas.dataset import DatasetItemCreateIn
from seedbank.services.dataset_service import DatasetService

pytestmark = pytest.mark.unit


def _make_actor(role: Role = Role.AI_DEVELOPER) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=uuid4(),
        email="ai@dev.com",
        role=role,
        is_active=True,
        is_verified=True,
        auth_method="jwt",
    )


class _FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0
        self.added: list[Any] = []

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1

    async def flush(self) -> None:
        pass

    async def rollback(self) -> None:
        self.rollbacks += 1


def _build_service() -> tuple[DatasetService, _FakeSession, MagicMock, MagicMock]:
    session = _FakeSession()
    datasets = MagicMock()
    datasets.get_by_name = AsyncMock(return_value=None)
    datasets.get_active = AsyncMock(return_value=None)
    datasets.add = AsyncMock(side_effect=lambda x: x)
    datasets.list_active = AsyncMock(return_value=[])
    datasets.count_active = AsyncMock(return_value=0)
    items = MagicMock()
    items.add_many = AsyncMock(return_value=None)
    items.list_for_dataset = AsyncMock(return_value=[])
    items.count_for_dataset = AsyncMock(return_value=0)
    svc = DatasetService(
        session=session,  # type: ignore[arg-type]
        datasets=datasets,
        items=items,
    )
    return svc, session, datasets, items


# ── create ────────────────────────────────────────────────────────────────


async def test_create_conflicts_when_name_exists() -> None:
    svc, _session, datasets, _items = _build_service()
    datasets.get_by_name = AsyncMock(return_value=MagicMock(id=uuid4(), name="x"))

    with pytest.raises(ConflictError):
        await svc.create(actor=_make_actor(), name="x", description=None)


async def test_create_translates_integrity_error_to_conflict() -> None:
    svc, session, datasets, _items = _build_service()
    datasets.add = AsyncMock(side_effect=IntegrityError("x", {}, Exception("uq")))

    with pytest.raises(ConflictError):
        await svc.create(actor=_make_actor(), name="x", description=None)
    assert session.rollbacks == 1


async def test_create_persists_and_commits() -> None:
    svc, session, datasets, _items = _build_service()
    out = await svc.create(actor=_make_actor(), name="x", description="desc")
    datasets.add.assert_awaited_once()
    assert session.commits == 1
    assert out.name == "x"
    assert out.description == "desc"


# ── get / add_items ────────────────────────────────────────────────────────


async def test_get_raises_not_found_when_missing() -> None:
    svc, _session, datasets, _items = _build_service()
    datasets.get_active = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError):
        await svc.get(uuid4())


async def test_add_items_raises_not_found_when_dataset_missing() -> None:
    svc, _session, datasets, _items = _build_service()
    datasets.get_active = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError):
        await svc.add_items(
            dataset_id=uuid4(),
            items=[DatasetItemCreateIn(image_storage_key="a")],
        )


async def test_add_items_rejects_duplicate_keys_in_payload() -> None:
    svc, _session, datasets, _items = _build_service()
    datasets.get_active = AsyncMock(return_value=MagicMock(id=uuid4()))

    with pytest.raises(ConflictError) as exc:
        await svc.add_items(
            dataset_id=uuid4(),
            items=[
                DatasetItemCreateIn(image_storage_key="dup"),
                DatasetItemCreateIn(image_storage_key="dup"),
            ],
        )
    assert "duplicate" in str(exc.value).lower()


async def test_add_items_translates_integrity_error_to_conflict() -> None:
    svc, session, datasets, items = _build_service()
    datasets.get_active = AsyncMock(return_value=MagicMock(id=uuid4()))
    items.add_many = AsyncMock(side_effect=IntegrityError("x", {}, Exception("uq")))

    with pytest.raises(ConflictError):
        await svc.add_items(
            dataset_id=uuid4(),
            items=[DatasetItemCreateIn(image_storage_key="k")],
        )
    assert session.rollbacks == 1


async def test_add_items_happy_path_commits_and_returns_count() -> None:
    svc, session, datasets, _items = _build_service()
    datasets.get_active = AsyncMock(return_value=MagicMock(id=uuid4()))

    n = await svc.add_items(
        dataset_id=uuid4(),
        items=[
            DatasetItemCreateIn(image_storage_key="a"),
            DatasetItemCreateIn(image_storage_key="b"),
            DatasetItemCreateIn(image_storage_key="c", ground_truth={"label": "good"}),
        ],
    )
    assert n == 3
    assert session.commits == 1
