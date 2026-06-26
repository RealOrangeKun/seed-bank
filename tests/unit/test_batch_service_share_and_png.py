"""Unit tests for the share-link + annotated-PNG paths of ``BatchService``.

Repos/storage/session are mocked. Covers: token creation commits and returns a
token; revoke clears it; the public ``get_shared_batch`` raises NotFound on an
unknown token; and the ``_draw_boxes`` renderer produces a valid PNG.
"""

from __future__ import annotations

import io
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from PIL import Image

from seedbank.core.config import get_settings
from seedbank.core.exceptions import NotFoundError
from seedbank.domain.user import AuthenticatedUser, Role
from seedbank.services.batch_service import BatchService, _draw_boxes

if TYPE_CHECKING:
    from seedbank.infrastructure.db.models import ScanBatch, SeedDetection

pytestmark = pytest.mark.unit


def _actor(role: Role = Role.END_USER) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=uuid4(),
        email="x@y.com",
        role=role,
        is_active=True,
        is_verified=True,
        scopes=frozenset(),
        auth_method="jwt",
    )


def _service() -> tuple[BatchService, MagicMock, MagicMock]:
    session = MagicMock()
    session.commit = AsyncMock()
    batches = MagicMock()
    batches.get = AsyncMock()
    batches.get_for_user = AsyncMock()
    batches.set_share_token = AsyncMock(return_value=True)
    batches.get_by_share_token = AsyncMock()
    svc = BatchService(
        session=session,
        batches=batches,
        images=MagicMock(),
        storage=MagicMock(),
        settings=get_settings(),
    )
    return svc, batches, session


class TestShareLinks:
    async def test_create_returns_token_and_commits(self) -> None:
        svc, batches, session = _service()
        actor = _actor()
        batches.get_for_user.return_value = SimpleNamespace(id=uuid4())

        token = await svc.create_share_link(batch_id=uuid4(), actor=actor)

        assert isinstance(token, str) and len(token) > 20
        # The token written to the repo is the one returned.
        assert batches.set_share_token.await_args.args[2] == token
        session.commit.assert_awaited_once()

    async def test_create_on_unowned_batch_raises_not_found(self) -> None:
        svc, batches, session = _service()
        batches.get_for_user.return_value = None  # owner resolution misses

        with pytest.raises(NotFoundError):
            await svc.create_share_link(batch_id=uuid4(), actor=_actor())
        session.commit.assert_not_called()

    async def test_revoke_clears_token(self) -> None:
        svc, batches, session = _service()
        batches.get_for_user.return_value = SimpleNamespace(id=uuid4())

        await svc.revoke_share_link(batch_id=uuid4(), actor=_actor())

        # Third positional arg to set_share_token is None on revoke.
        assert batches.set_share_token.await_args.args[2] is None
        session.commit.assert_awaited_once()

    async def test_get_shared_unknown_token_raises_not_found(self) -> None:
        svc, batches, _session = _service()
        batches.get_by_share_token.return_value = None

        with pytest.raises(NotFoundError):
            await svc.get_shared_batch(token="nope")

    async def test_get_shared_returns_batch(self) -> None:
        svc, batches, _session = _service()
        batch = cast("ScanBatch", SimpleNamespace(id=uuid4()))
        batches.get_by_share_token.return_value = batch

        result = await svc.get_shared_batch(token="good-token")
        assert result is batch
        batches.get_by_share_token.assert_awaited_once_with("good-token")


class TestDrawBoxes:
    def _png(self, w: int = 120, h: int = 90) -> bytes:
        buf = io.BytesIO()
        Image.new("RGB", (w, h), (210, 210, 210)).save(buf, format="PNG")
        return buf.getvalue()

    def test_returns_valid_png_same_size(self) -> None:
        det = SimpleNamespace(
            box_x_norm=0.1, box_y_norm=0.2, box_w_norm=0.3, box_h_norm=0.25, quality="good"
        )
        out = _draw_boxes(self._png(120, 90), cast("list[SeedDetection]", [det]))
        assert out[:4] == b"\x89PNG"
        img = Image.open(io.BytesIO(out))
        assert img.size == (120, 90)  # original dimensions preserved

    def test_no_detections_still_returns_png(self) -> None:
        out = _draw_boxes(self._png(), [])
        assert out[:4] == b"\x89PNG"

    def test_handles_each_quality_color(self) -> None:
        dets = [
            SimpleNamespace(
                box_x_norm=0.0, box_y_norm=0.0, box_w_norm=0.5, box_h_norm=0.5, quality=q
            )
            for q in ("good", "bad", None)
        ]
        out = _draw_boxes(self._png(), cast("list[SeedDetection]", dets))
        assert out[:4] == b"\x89PNG"
