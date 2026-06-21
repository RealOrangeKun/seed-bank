"""Unit tests for ``BatchService`` delete + export (ported master features).

Covers the three methods added when the data-management endpoints were
ported onto the rewrite's architecture:

- :meth:`BatchService.delete_for_user` — single soft-delete, owner + admin
- :meth:`BatchService.bulk_delete_for_user` — best-effort bulk soft-delete
- :meth:`BatchService.detections_for_export` — flat detection list for CSV/JSON

The ownership contract mirrors ``image_urls_for_user`` /
``test_batch_service_image_urls.py``: owners act on their own batches, admins
on any, and the miss case is always ``NotFoundError`` (404, never 403) so IDs
can't be probed. Session, repos, and storage are mocked — a unit test never
touches a DB or network. ``session.commit`` is asserted on the write paths
because that's the rewrite's convention (services commit; the request-scoped
session rolls back on error).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from seedbank.core.config import get_settings
from seedbank.core.exceptions import NotFoundError
from seedbank.domain.user import AuthenticatedUser, Role
from seedbank.services.batch_service import BatchService

pytestmark = pytest.mark.unit


def _make_actor(role: Role = Role.END_USER) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=uuid4(),
        email="x@y.com",
        role=role,
        is_active=True,
        is_verified=True,
        scopes=frozenset(),
        auth_method="jwt",
    )


def _build_service() -> tuple[BatchService, MagicMock, MagicMock, MagicMock]:
    """Service with mocked session + repos + storage.

    Returns ``(svc, batches, images, session)`` — the three handles a test
    needs to arrange repo returns and assert ``commit``.
    """
    session = MagicMock()
    session.commit = AsyncMock()
    batches = MagicMock()
    batches.get = AsyncMock()
    batches.get_for_user = AsyncMock()
    batches.soft_delete_for_user = AsyncMock()
    batches.soft_delete_many_for_user = AsyncMock()
    batches.soft_delete_many_any_owner = AsyncMock()
    batches.list_detections_for_batch = AsyncMock(return_value=[])
    images = MagicMock()
    storage = MagicMock()
    svc = BatchService(
        session=session,  # type: ignore[arg-type]
        batches=batches,
        images=images,
        storage=storage,
        settings=get_settings(),
    )
    return svc, batches, images, session


# ── delete_for_user ─────────────────────────────────────────────────────────


class TestDeleteForUser:
    async def test_owner_soft_deletes_own_batch_and_commits(self) -> None:
        svc, batches, _images, session = _build_service()
        actor = _make_actor(Role.END_USER)
        batch_id = uuid4()
        # ``_owner_id_for`` confirms existence via the scoped read first.
        batches.get_for_user.return_value = SimpleNamespace(id=batch_id)
        batches.soft_delete_for_user.return_value = True

        await svc.delete_for_user(batch_id=batch_id, actor=actor)

        batches.soft_delete_for_user.assert_awaited_once_with(batch_id, actor.id)
        session.commit.assert_awaited_once()

    async def test_non_owner_gets_not_found_and_no_commit(self) -> None:
        svc, batches, _images, session = _build_service()
        actor = _make_actor(Role.END_USER)
        # Scoped read misses → owner resolution raises before any delete.
        batches.get_for_user.return_value = None

        with pytest.raises(NotFoundError):
            await svc.delete_for_user(batch_id=uuid4(), actor=actor)

        batches.soft_delete_for_user.assert_not_called()
        session.commit.assert_not_called()

    async def test_admin_deletes_any_batch_via_resolved_owner(self) -> None:
        svc, batches, _images, session = _build_service()
        actor = _make_actor(Role.ADMIN)
        batch_id = uuid4()
        other_owner = uuid4()
        # Admin resolves the real owner through the unscoped get.
        batches.get.return_value = SimpleNamespace(
            id=batch_id, user_id=other_owner, deleted_at=None
        )
        batches.soft_delete_for_user.return_value = True

        await svc.delete_for_user(batch_id=batch_id, actor=actor)

        batches.get.assert_awaited_once_with(batch_id)
        batches.get_for_user.assert_not_called()
        # Deletes against the *owner's* id, not the admin's.
        batches.soft_delete_for_user.assert_awaited_once_with(batch_id, other_owner)
        session.commit.assert_awaited_once()

    async def test_admin_missing_batch_raises_not_found(self) -> None:
        svc, batches, _images, session = _build_service()
        actor = _make_actor(Role.ADMIN)
        batches.get.return_value = None

        with pytest.raises(NotFoundError):
            await svc.delete_for_user(batch_id=uuid4(), actor=actor)

        batches.soft_delete_for_user.assert_not_called()
        session.commit.assert_not_called()

    async def test_admin_already_deleted_batch_raises_not_found(self) -> None:
        """An already soft-deleted batch is invisible even to admin delete."""
        svc, batches, _images, session = _build_service()
        actor = _make_actor(Role.ADMIN)
        batches.get.return_value = SimpleNamespace(id=uuid4(), user_id=uuid4(), deleted_at=object())

        with pytest.raises(NotFoundError):
            await svc.delete_for_user(batch_id=uuid4(), actor=actor)

        batches.soft_delete_for_user.assert_not_called()

    async def test_second_delete_is_a_miss_when_repo_flips_nothing(self) -> None:
        """If the row was already deleted, the scoped read still found it but
        the UPDATE flips zero rows → ``NotFoundError`` (idempotent at storage,
        404 at the API)."""
        svc, batches, _images, session = _build_service()
        actor = _make_actor(Role.END_USER)
        batches.get_for_user.return_value = SimpleNamespace(id=uuid4())
        batches.soft_delete_for_user.return_value = False

        with pytest.raises(NotFoundError):
            await svc.delete_for_user(batch_id=uuid4(), actor=actor)

        session.commit.assert_not_called()


# ── bulk_delete_for_user ────────────────────────────────────────────────────


class TestBulkDeleteForUser:
    async def test_empty_list_short_circuits_without_repo_or_commit(self) -> None:
        svc, batches, _images, session = _build_service()
        actor = _make_actor(Role.END_USER)

        deleted = await svc.bulk_delete_for_user(batch_ids=[], actor=actor)

        assert deleted == 0
        batches.soft_delete_many_for_user.assert_not_called()
        batches.soft_delete_many_any_owner.assert_not_called()
        session.commit.assert_not_called()

    async def test_owner_bulk_delete_uses_scoped_repo_and_commits(self) -> None:
        svc, batches, _images, session = _build_service()
        actor = _make_actor(Role.END_USER)
        ids = [uuid4(), uuid4(), uuid4()]
        batches.soft_delete_many_for_user.return_value = 2  # one was unowned

        deleted = await svc.bulk_delete_for_user(batch_ids=ids, actor=actor)

        assert deleted == 2
        batches.soft_delete_many_for_user.assert_awaited_once_with(ids, actor.id)
        batches.soft_delete_many_any_owner.assert_not_called()
        session.commit.assert_awaited_once()

    async def test_duplicate_ids_are_deduped_before_the_repo_call(self) -> None:
        svc, batches, _images, session = _build_service()
        actor = _make_actor(Role.END_USER)
        a, b = uuid4(), uuid4()
        batches.soft_delete_many_for_user.return_value = 2

        await svc.bulk_delete_for_user(batch_ids=[a, b, a, b, a], actor=actor)

        sent_ids = batches.soft_delete_many_for_user.await_args.args[0]
        assert sent_ids == [a, b]  # order preserved, dups removed

    async def test_admin_bulk_delete_uses_unscoped_repo(self) -> None:
        svc, batches, _images, session = _build_service()
        actor = _make_actor(Role.ADMIN)
        ids = [uuid4(), uuid4()]
        batches.soft_delete_many_any_owner.return_value = 2

        deleted = await svc.bulk_delete_for_user(batch_ids=ids, actor=actor)

        assert deleted == 2
        batches.soft_delete_many_any_owner.assert_awaited_once_with(ids)
        batches.soft_delete_many_for_user.assert_not_called()
        session.commit.assert_awaited_once()


# ── detections_for_export ───────────────────────────────────────────────────


class TestDetectionsForExport:
    async def test_owner_export_returns_repo_rows(self) -> None:
        svc, batches, _images, _session = _build_service()
        actor = _make_actor(Role.END_USER)
        batch_id = uuid4()
        batches.get_for_user.return_value = SimpleNamespace(id=batch_id)
        rows = [SimpleNamespace(id=uuid4()), SimpleNamespace(id=uuid4())]
        batches.list_detections_for_batch.return_value = rows

        result = await svc.detections_for_export(batch_id=batch_id, actor=actor)

        assert result == rows
        batches.list_detections_for_batch.assert_awaited_once_with(batch_id, actor.id)

    async def test_non_owner_export_raises_not_found(self) -> None:
        svc, batches, _images, _session = _build_service()
        actor = _make_actor(Role.END_USER)
        batches.get_for_user.return_value = None

        with pytest.raises(NotFoundError):
            await svc.detections_for_export(batch_id=uuid4(), actor=actor)

        batches.list_detections_for_batch.assert_not_called()

    async def test_admin_export_resolves_owner_then_lists(self) -> None:
        svc, batches, _images, _session = _build_service()
        actor = _make_actor(Role.ADMIN)
        batch_id = uuid4()
        owner = uuid4()
        batches.get.return_value = SimpleNamespace(id=batch_id, user_id=owner, deleted_at=None)
        batches.list_detections_for_batch.return_value = []

        await svc.detections_for_export(batch_id=batch_id, actor=actor)

        batches.list_detections_for_batch.assert_awaited_once_with(batch_id, owner)

    async def test_empty_batch_exports_empty_list(self) -> None:
        svc, batches, _images, _session = _build_service()
        actor = _make_actor(Role.END_USER)
        batches.get_for_user.return_value = SimpleNamespace(id=uuid4())
        batches.list_detections_for_batch.return_value = []

        result = await svc.detections_for_export(batch_id=uuid4(), actor=actor)

        assert result == []
