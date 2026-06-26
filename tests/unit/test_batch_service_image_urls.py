"""Unit tests for ``services.batch_service.BatchService.image_urls_for_user``.

These pin the ownership rule (admin reads any batch; everyone else only
their own, with ``NotFoundError`` — never a 403 — on the cross-user case)
and the URL-minting contract (one :class:`ImageUrl` per image, presigned
against the images bucket, ``expires_at`` in the future).

The session, repos, and MinIO storage are all mocked: a unit test must
not touch a network or a database. The storage stub exposes an async
``presigned_get_url`` exactly as :class:`MinioStorage` does — we never
mock ``AsyncSession`` as if it were the real thing; the service only
holds the session, it doesn't call it on this path.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from seedbank.core.config import get_settings
from seedbank.core.exceptions import NotFoundError
from seedbank.domain.user import AuthenticatedUser, Role
from seedbank.services.batch_service import BatchService, ImageUrl

pytestmark = pytest.mark.unit


# ── Helpers ────────────────────────────────────────────────────────────────


_STUB_URL = "https://minio.test/presigned"


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


def _fake_image(storage_key: str) -> SimpleNamespace:
    """A lightweight stand-in for a ``ScanImage`` ORM row.

    ``image_urls_for_user`` only reads ``.id`` and ``.storage_key`` off
    each image, so a namespace with those two attributes is enough — no
    need to construct (and thus over-couple to) the full ORM model.
    """
    return SimpleNamespace(id=uuid4(), storage_key=storage_key)


def _build_service() -> tuple[BatchService, MagicMock, MagicMock, MagicMock]:
    """Construct the service with mocked repos + storage.

    Mirrors ``tests/unit/test_analysis_service.py``: a ``MagicMock``
    session placeholder (never called on this path), repo mocks whose
    async methods are ``AsyncMock``, and a storage stub whose
    ``presigned_get_url`` returns a fixed URL.
    """
    session = MagicMock()
    batches = MagicMock()
    batches.get = AsyncMock()
    batches.get_for_user = AsyncMock()
    images = MagicMock()
    images.list_for_batch = AsyncMock(return_value=[])
    storage = MagicMock()
    storage.presigned_get_url = AsyncMock(return_value=_STUB_URL)
    svc = BatchService(
        session=session,
        batches=batches,
        images=images,
        storage=storage,
        settings=get_settings(),
    )
    return svc, batches, images, storage


# ── Happy path ─────────────────────────────────────────────────────────────


class TestHappyPath:
    async def test_owner_gets_one_image_url_per_image_with_future_expiry(self) -> None:
        svc, batches, images, _storage = _build_service()
        actor = _make_actor(Role.END_USER)
        batches.get_for_user.return_value = SimpleNamespace(id=uuid4())
        imgs = [_fake_image("a/1.png"), _fake_image("a/2.png")]
        images.list_for_batch.return_value = imgs
        before = datetime.now(UTC)

        result = await svc.image_urls_for_user(batch_id=uuid4(), actor=actor)

        assert len(result) == len(imgs)
        assert all(isinstance(u, ImageUrl) for u in result)
        assert [u.image_id for u in result] == [img.id for img in imgs]
        assert all(u.url == _STUB_URL for u in result)
        assert all(u.expires_at > before for u in result)

    async def test_owner_path_uses_ownership_scoped_query_not_admin_get(self) -> None:
        svc, batches, images, _storage = _build_service()
        actor = _make_actor(Role.END_USER)
        batch_id = uuid4()
        batches.get_for_user.return_value = SimpleNamespace(id=batch_id)
        images.list_for_batch.return_value = [_fake_image("a/1.png")]

        await svc.image_urls_for_user(batch_id=batch_id, actor=actor)

        batches.get_for_user.assert_awaited_once_with(batch_id, actor.id)
        batches.get.assert_not_called()

    async def test_admin_loads_any_batch_via_unscoped_get(self) -> None:
        svc, batches, images, _storage = _build_service()
        actor = _make_actor(Role.ADMIN)
        batch_id = uuid4()
        batches.get.return_value = SimpleNamespace(id=batch_id)
        images.list_for_batch.return_value = [_fake_image("a/1.png")]

        result = await svc.image_urls_for_user(batch_id=batch_id, actor=actor)

        batches.get.assert_awaited_once_with(batch_id)
        batches.get_for_user.assert_not_called()
        assert len(result) == 1

    async def test_presign_called_with_images_bucket_and_each_storage_key(self) -> None:
        svc, batches, images, storage = _build_service()
        actor = _make_actor(Role.END_USER)
        batches.get_for_user.return_value = SimpleNamespace(id=uuid4())
        imgs = [_fake_image("a/1.png"), _fake_image("a/2.png")]
        images.list_for_batch.return_value = imgs

        await svc.image_urls_for_user(batch_id=uuid4(), actor=actor)

        bucket = svc.settings.minio_bucket_images
        assert storage.presigned_get_url.await_count == len(imgs)
        called_buckets = [c.args[0] for c in storage.presigned_get_url.await_args_list]
        called_keys = [c.args[1] for c in storage.presigned_get_url.await_args_list]
        assert called_buckets == [bucket, bucket]
        assert called_keys == [img.storage_key for img in imgs]


# ── Empty batch ────────────────────────────────────────────────────────────


class TestEmptyBatch:
    async def test_batch_with_no_images_returns_empty_list(self) -> None:
        svc, batches, images, storage = _build_service()
        actor = _make_actor(Role.END_USER)
        batches.get_for_user.return_value = SimpleNamespace(id=uuid4())
        images.list_for_batch.return_value = []

        result = await svc.image_urls_for_user(batch_id=uuid4(), actor=actor)

        assert result == []
        storage.presigned_get_url.assert_not_called()


# ── Ownership / existence ──────────────────────────────────────────────────


class TestNotFound:
    async def test_missing_batch_for_admin_raises_not_found(self) -> None:
        svc, batches, images, storage = _build_service()
        actor = _make_actor(Role.ADMIN)
        batches.get.return_value = None

        with pytest.raises(NotFoundError):
            await svc.image_urls_for_user(batch_id=uuid4(), actor=actor)

        images.list_for_batch.assert_not_called()
        storage.presigned_get_url.assert_not_called()

    async def test_non_owner_gets_not_found_not_forbidden(self) -> None:
        """A non-admin whose ownership-scoped query returns ``None`` gets
        ``NotFoundError`` so batch IDs can't be probed (404, never 403)."""
        svc, batches, images, storage = _build_service()
        actor = _make_actor(Role.END_USER)
        batches.get_for_user.return_value = None

        with pytest.raises(NotFoundError):
            await svc.image_urls_for_user(batch_id=uuid4(), actor=actor)

        images.list_for_batch.assert_not_called()
        storage.presigned_get_url.assert_not_called()
