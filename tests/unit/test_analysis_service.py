"""Unit tests for ``services.analysis_service.AnalysisService``.

These pin the validation rules — file count, mime, size, decode, and the
``model_id`` override authorization — at the layer that owns them. The
session, repos, MinIO, and Celery dispatch are all mocked: a unit test
must not touch a network or a database.
"""

from __future__ import annotations

import io
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from PIL import Image

from seedbank.core.config import get_settings
from seedbank.core.exceptions import ForbiddenError, ValidationError
from seedbank.domain.user import AuthenticatedUser, Role
from seedbank.services.analysis_service import AnalysisService, AnalyzeFile

pytestmark = pytest.mark.unit


# ── Helpers ────────────────────────────────────────────────────────────────


def _png_bytes(*, size: tuple[int, int] = (8, 8)) -> bytes:
    """Minimum-viable PNG bytes for the validator to accept."""
    img = Image.new("RGB", size, color=(120, 200, 80))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_actor(role: Role = Role.END_USER) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=uuid4(),
        email="x@y.com",
        role=role,
        is_active=True,
        is_verified=True,
        auth_method="jwt",
    )


class _FakeSession:
    """Records ``add`` / ``commit`` calls so tests can assert ordering."""

    def __init__(self) -> None:
        self.added: list[Any] = []
        self.commits = 0

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1

    async def flush(self) -> None:
        pass

    async def rollback(self) -> None:
        pass


def _build_service() -> tuple[AnalysisService, _FakeSession, MagicMock, MagicMock, AsyncMock]:
    session = _FakeSession()
    batches = MagicMock()
    batches.add = AsyncMock(side_effect=lambda x: x)
    images = MagicMock()
    images.add = AsyncMock(side_effect=lambda x: x)
    storage = MagicMock()
    storage.put_object = AsyncMock()
    svc = AnalysisService(
        session=session,  # type: ignore[arg-type]
        batches=batches,
        images=images,
        settings=get_settings(),
        storage=storage,
    )
    return svc, session, batches, images, storage


# ── Authorization on model_id override ─────────────────────────────────────


class TestModelIdOverrideAuthz:
    @pytest.mark.asyncio
    async def test_end_user_with_override_is_forbidden(self) -> None:
        svc, *_ = _build_service()
        with pytest.raises(ForbiddenError):
            await svc.create_and_dispatch(
                actor=_make_actor(Role.END_USER),
                files=[AnalyzeFile(filename="x.png", content_type="image/png", data=_png_bytes())],
                supplier_id=None,
                seed_type_id=None,
                model_id_override=uuid4(),
                gps_lat=None,
                gps_long=None,
                country_code=None,
                ip=None,
            )

    @pytest.mark.asyncio
    async def test_ai_developer_with_override_proceeds(self) -> None:
        svc, session, _batches, _images, _storage = _build_service()
        with patch("seedbank.services.analysis_service.celery_app.send_task") as send:
            await svc.create_and_dispatch(
                actor=_make_actor(Role.AI_DEVELOPER),
                files=[AnalyzeFile(filename="x.png", content_type="image/png", data=_png_bytes())],
                supplier_id=None,
                seed_type_id=None,
                model_id_override=uuid4(),
                gps_lat=None,
                gps_long=None,
                country_code=None,
                ip=None,
            )
        assert send.called
        assert session.commits == 1

    @pytest.mark.asyncio
    async def test_admin_with_override_proceeds(self) -> None:
        svc, *_ = _build_service()
        with patch("seedbank.services.analysis_service.celery_app.send_task"):
            await svc.create_and_dispatch(
                actor=_make_actor(Role.ADMIN),
                files=[AnalyzeFile(filename="x.png", content_type="image/png", data=_png_bytes())],
                supplier_id=None,
                seed_type_id=None,
                model_id_override=uuid4(),
                gps_lat=None,
                gps_long=None,
                country_code=None,
                ip=None,
            )

    @pytest.mark.asyncio
    async def test_end_user_without_override_proceeds(self) -> None:
        """End users analyze fine; the gate is *only* on model_id."""
        svc, *_ = _build_service()
        with patch("seedbank.services.analysis_service.celery_app.send_task"):
            await svc.create_and_dispatch(
                actor=_make_actor(Role.END_USER),
                files=[AnalyzeFile(filename="x.png", content_type="image/png", data=_png_bytes())],
                supplier_id=None,
                seed_type_id=None,
                model_id_override=None,
                gps_lat=None,
                gps_long=None,
                country_code=None,
                ip=None,
            )


# ── File-count validation ──────────────────────────────────────────────────


class TestFileCountValidation:
    @pytest.mark.asyncio
    async def test_zero_files_rejected(self) -> None:
        svc, *_ = _build_service()
        with pytest.raises(ValidationError):
            await svc.create_and_dispatch(
                actor=_make_actor(),
                files=[],
                supplier_id=None,
                seed_type_id=None,
                model_id_override=None,
                gps_lat=None,
                gps_long=None,
                country_code=None,
                ip=None,
            )

    @pytest.mark.asyncio
    async def test_above_max_files_rejected(self) -> None:
        svc, *_ = _build_service()
        max_files = svc.settings.analyze_max_files_per_request
        files = [
            AnalyzeFile(filename=f"x{i}.png", content_type="image/png", data=_png_bytes())
            for i in range(max_files + 1)
        ]
        with pytest.raises(ValidationError) as ei:
            await svc.create_and_dispatch(
                actor=_make_actor(),
                files=files,
                supplier_id=None,
                seed_type_id=None,
                model_id_override=None,
                gps_lat=None,
                gps_long=None,
                country_code=None,
                ip=None,
            )
        assert str(max_files) in str(ei.value)


# ── Per-file validation ────────────────────────────────────────────────────


class TestPerFileValidation:
    @pytest.mark.asyncio
    async def test_unknown_mime_rejected(self) -> None:
        svc, *_ = _build_service()
        with pytest.raises(ValidationError):
            await svc.create_and_dispatch(
                actor=_make_actor(),
                files=[AnalyzeFile(filename="x.bmp", content_type="image/bmp", data=_png_bytes())],
                supplier_id=None,
                seed_type_id=None,
                model_id_override=None,
                gps_lat=None,
                gps_long=None,
                country_code=None,
                ip=None,
            )

    @pytest.mark.asyncio
    async def test_oversized_file_rejected(self) -> None:
        svc, *_ = _build_service()
        # Forge bytes larger than the cap; content type still PNG so the
        # size check fires before the decode check.
        oversized = b"\x89PNG\r\n\x1a\n" + b"\x00" * (svc.settings.analyze_max_image_bytes + 1)
        with pytest.raises(ValidationError) as ei:
            await svc.create_and_dispatch(
                actor=_make_actor(),
                files=[AnalyzeFile(filename="big.png", content_type="image/png", data=oversized)],
                supplier_id=None,
                seed_type_id=None,
                model_id_override=None,
                gps_lat=None,
                gps_long=None,
                country_code=None,
                ip=None,
            )
        assert "max size" in str(ei.value)

    @pytest.mark.asyncio
    async def test_undecodable_image_rejected(self) -> None:
        svc, *_ = _build_service()
        with pytest.raises(ValidationError):
            await svc.create_and_dispatch(
                actor=_make_actor(),
                files=[
                    AnalyzeFile(filename="x.png", content_type="image/png", data=b"not-an-image")
                ],
                supplier_id=None,
                seed_type_id=None,
                model_id_override=None,
                gps_lat=None,
                gps_long=None,
                country_code=None,
                ip=None,
            )


# ── Happy path side effects ────────────────────────────────────────────────


class TestHappyPath:
    @pytest.mark.asyncio
    async def test_single_file_writes_minio_then_commits_then_dispatches(self) -> None:
        svc, session, _batches, _images, storage = _build_service()
        with patch("seedbank.services.analysis_service.celery_app.send_task") as send:
            await svc.create_and_dispatch(
                actor=_make_actor(),
                files=[AnalyzeFile(filename="a.png", content_type="image/png", data=_png_bytes())],
                supplier_id=None,
                seed_type_id=None,
                model_id_override=None,
                gps_lat=None,
                gps_long=None,
                country_code=None,
                ip="127.0.0.1",
            )
        # Ordering invariants.
        storage.put_object.assert_awaited_once()
        assert session.commits == 1
        # Two dispatches per batch: one analyze_image (per image) plus a DWH
        # ``sync_scan_batch`` so the warehouse picks up the pending row.
        assert send.call_count == 2
        task_names = [call.args[0] for call in send.call_args_list]
        assert "seedbank.analyze_image" in task_names
        assert "seedbank.dwh.sync_scan_batch" in task_names

    @pytest.mark.asyncio
    async def test_three_files_dispatch_three_tasks(self) -> None:
        svc, session, _b, _i, storage = _build_service()
        with patch("seedbank.services.analysis_service.celery_app.send_task") as send:
            await svc.create_and_dispatch(
                actor=_make_actor(),
                files=[
                    AnalyzeFile(filename=f"a{i}.png", content_type="image/png", data=_png_bytes())
                    for i in range(3)
                ],
                supplier_id=None,
                seed_type_id=None,
                model_id_override=None,
                gps_lat=None,
                gps_long=None,
                country_code=None,
                ip=None,
            )
        assert storage.put_object.await_count == 3
        # 3 analyze_image dispatches + 1 sync_scan_batch dispatch
        assert send.call_count == 4
        task_names = [call.args[0] for call in send.call_args_list]
        assert task_names.count("seedbank.analyze_image") == 3
        assert task_names.count("seedbank.dwh.sync_scan_batch") == 1
        assert session.commits == 1  # one commit covers all three images

    @pytest.mark.asyncio
    async def test_audit_row_recorded(self) -> None:
        svc, session, *_ = _build_service()
        with patch("seedbank.services.analysis_service.celery_app.send_task"):
            await svc.create_and_dispatch(
                actor=_make_actor(),
                files=[AnalyzeFile(filename="a.png", content_type="image/png", data=_png_bytes())],
                supplier_id=None,
                seed_type_id=None,
                model_id_override=None,
                gps_lat=None,
                gps_long=None,
                country_code=None,
                ip="10.0.0.5",
            )
        # AuditLog row is the only object the service ``add()``s on the
        # session directly (batch + images go through repos).
        actions = [getattr(o, "action", None) for o in session.added]
        assert "analyze.dispatched" in actions


# ── Video branch ────────────────────────────────────────────────────────────


def _video_file(content_type: str = "video/mp4", data: bytes = b"fake-mp4-bytes") -> AnalyzeFile:
    return AnalyzeFile(filename="clip.mp4", content_type=content_type, data=data)


class TestVideoBranch:
    @pytest.mark.asyncio
    async def test_single_video_stores_then_commits_then_dispatches_video_task(self) -> None:
        svc, session, _b, images, storage = _build_service()
        with patch("seedbank.services.analysis_service.celery_app.send_task") as send:
            await svc.create_and_dispatch(
                actor=_make_actor(),
                files=[_video_file()],
                supplier_id=None,
                seed_type_id=None,
                model_id_override=None,
                gps_lat=None,
                gps_long=None,
                country_code=None,
                ip="127.0.0.1",
            )
        # The raw video is written once; no scan_images are created here (the
        # worker extracts frames), and exactly one commit happens.
        storage.put_object.assert_awaited_once()
        images.add.assert_not_called()
        assert session.commits == 1
        task_names = [call.args[0] for call in send.call_args_list]
        assert "seedbank.analyze_video" in task_names
        assert "seedbank.dwh.sync_scan_batch" in task_names
        assert "seedbank.analyze_image" not in task_names

    @pytest.mark.asyncio
    async def test_video_audit_row_recorded(self) -> None:
        svc, session, *_ = _build_service()
        with patch("seedbank.services.analysis_service.celery_app.send_task"):
            await svc.create_and_dispatch(
                actor=_make_actor(),
                files=[_video_file()],
                supplier_id=None,
                seed_type_id=None,
                model_id_override=None,
                gps_lat=None,
                gps_long=None,
                country_code=None,
                ip=None,
            )
        actions = [getattr(o, "action", None) for o in session.added]
        assert "analyze.dispatched_video" in actions

    @pytest.mark.asyncio
    async def test_video_mixed_with_image_rejected(self) -> None:
        svc, *_ = _build_service()
        with pytest.raises(ValidationError):
            await svc.create_and_dispatch(
                actor=_make_actor(),
                files=[
                    _video_file(),
                    AnalyzeFile(filename="a.png", content_type="image/png", data=_png_bytes()),
                ],
                supplier_id=None,
                seed_type_id=None,
                model_id_override=None,
                gps_lat=None,
                gps_long=None,
                country_code=None,
                ip=None,
            )

    @pytest.mark.asyncio
    async def test_oversized_video_rejected(self) -> None:
        svc, *_ = _build_service()
        oversized = b"\x00" * (svc.settings.analyze_max_video_bytes + 1)
        with pytest.raises(ValidationError) as ei:
            await svc.create_and_dispatch(
                actor=_make_actor(),
                files=[_video_file(data=oversized)],
                supplier_id=None,
                seed_type_id=None,
                model_id_override=None,
                gps_lat=None,
                gps_long=None,
                country_code=None,
                ip=None,
            )
        assert "max size" in str(ei.value)
