"""Analysis service — the unified ``POST /analyze`` use case.

The router parses the multipart body, reads each ``UploadFile`` into
memory, and hands the byte buffers to :class:`AnalysisService`.
Everything from validation through MinIO upload through Celery dispatch
happens here so the router stays a thin parse-and-return shell.

Ordering is load-bearing:

1. Validate every file *before* any side effect — a single 13 MB file
   in a 5-file batch must reject the whole batch, not stash four objects.
2. Write to MinIO *before* committing the DB rows. A successful commit
   then guarantees that every ``scan_images.storage_key`` references a
   reachable object. If MinIO fails partway through, the DB transaction
   rolls back and Celery is never asked to process orphan rows.
3. Dispatch to Celery *only after* the DB commit. The worker reads
   ``scan_images`` by id; sending the task before the row is visible
   would race the worker.

The service raises domain exceptions (:mod:`seedbank.core.exceptions`)
only — the router's exception handler maps them to RFC 9457 Problem
Details. ``HTTPException`` is forbidden here.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from io import BytesIO
from typing import TYPE_CHECKING

from PIL import Image, UnidentifiedImageError

from seedbank.core.exceptions import ForbiddenError, ValidationError
from seedbank.core.ids import uuid7
from seedbank.core.logging import get_logger
from seedbank.domain.user import Role
from seedbank.infrastructure.db.enums import BatchSource, BatchStatus, LocationSource
from seedbank.infrastructure.db.models import AuditLog, ScanBatch, ScanImage
from seedbank.workers.celery_app import celery_app

if TYPE_CHECKING:
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from seedbank.core.config import Settings
    from seedbank.domain.user import AuthenticatedUser
    from seedbank.infrastructure.db.repositories import (
        ScanBatchRepository,
        ScanImageRepository,
    )
    from seedbank.infrastructure.storage import MinioStorage

log = get_logger(__name__)

# MIME → file extension. Used to construct deterministic storage keys
# without trusting the client filename.
_MIME_TO_EXT: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

_ANALYZE_TASK_NAME = "seedbank.analyze_image"
_ANALYZE_TASK_QUEUE = "inference"


@dataclass(frozen=True, slots=True)
class AnalyzeFile:
    """An in-memory file the router has already read.

    ``data`` is the raw bytes — the router pulls them out of the
    ``UploadFile`` so the service stays free of FastAPI types and is
    trivial to unit-test.
    """

    filename: str | None
    content_type: str
    data: bytes


class AnalysisService:
    """Orchestrates upload + batch creation + Celery dispatch."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        batches: ScanBatchRepository,
        images: ScanImageRepository,
        settings: Settings,
        storage: MinioStorage,
    ) -> None:
        self.session = session
        self.batches = batches
        self.images = images
        self.settings = settings
        self.storage = storage

    async def create_and_dispatch(
        self,
        *,
        actor: AuthenticatedUser,
        files: list[AnalyzeFile],
        supplier_id: UUID | None,
        seed_type_id: UUID | None,
        model_id_override: UUID | None,
        gps_lat: Decimal | None,
        gps_long: Decimal | None,
        country_code: str | None,
        ip: str | None,
        mode: str | None = None,
        source: str | None = None,
    ) -> ScanBatch:
        """Validate, persist, and dispatch one analyze request.

        Returns the persisted :class:`ScanBatch`. ``image_count`` for the
        response envelope equals ``len(files)``; the router sets it on
        the schema after this method returns.
        """
        self._authorize_override(actor=actor, model_id_override=model_id_override)
        self._validate_file_count(files)

        # Phase 1 — pure validation. Nothing has been written yet.
        prepared = [self._validate_and_prepare(f) for f in files]

        # Phase 2 — build the batch + image rows in memory.
        batch = self._build_batch(
            actor=actor,
            supplier_id=supplier_id,
            gps_lat=gps_lat,
            gps_long=gps_long,
            country_code=country_code,
            source=source,
        )
        await self.batches.add(batch)

        images_to_dispatch: list[ScanImage] = []
        for prep in prepared:
            image_id = uuid7()
            image = ScanImage(
                id=image_id,
                batch_id=batch.id,
                storage_key=self._make_storage_key(batch.id, image_id, prep.content_type),
                content_type=prep.content_type,
                size_bytes=prep.size_bytes,
                sha256=prep.sha256,
                width=prep.width,
                height=prep.height,
            )
            # Phase 3 — push to MinIO before commit. A failure here
            # raises ExternalServiceError; the open transaction is
            # rolled back by the request scope and the user gets a 503.
            await self.storage.put_object(
                self.settings.minio_bucket_images,
                image.storage_key,
                prep.data,
                prep.content_type,
            )
            await self.images.add(image)
            images_to_dispatch.append(image)

        self.session.add(
            AuditLog(
                actor_id=actor.id,
                action="analyze.dispatched",
                target_type="scan_batch",
                target_id=str(batch.id),
                audit_metadata={
                    "image_count": len(prepared),
                    "model_id_override": (str(model_id_override) if model_id_override else None),
                    "seed_type_id": str(seed_type_id) if seed_type_id else None,
                },
                ip=ip,
            )
        )

        # Phase 4 — commit. Only after this do workers see the rows.
        await self.session.commit()

        # Phase 5 — dispatch one Celery task per image. The task name
        # is hard-coded (string contract); we never import the worker
        # module from the API process to keep the boundary clean.
        for image in images_to_dispatch:
            celery_app.send_task(
                _ANALYZE_TASK_NAME,
                args=[
                    str(image.id),
                    str(model_id_override) if model_id_override else None,
                    str(seed_type_id) if seed_type_id else None,
                    mode,
                ],
                queue=_ANALYZE_TASK_QUEUE,
            )

        # Phase 6 — DWH dual-write. Best-effort; broker failures are logged
        # but never break the API response (the OLTP commit already won).
        # local import: workers package may not be importable in test contexts
        from seedbank.workers.tasks.dwh import (
            SYNC_SCAN_BATCH,
            dispatch_after_commit,
        )

        dispatch_after_commit(SYNC_SCAN_BATCH, str(batch.id))

        log.info(
            "analyze.created",
            batch_id=str(batch.id),
            image_count=len(prepared),
            user_id=str(actor.id),
            model_id_override=(str(model_id_override) if model_id_override else None),
            seed_type_id=str(seed_type_id) if seed_type_id else None,
        )
        return batch

    # ── Internals ───────────────────────────────────────────────────────────

    def _authorize_override(
        self,
        *,
        actor: AuthenticatedUser,
        model_id_override: UUID | None,
    ) -> None:
        if model_id_override is None:
            return
        if actor.role is Role.ADMIN or actor.role is Role.AI_DEVELOPER:
            return
        raise ForbiddenError("Only ai_developer or admin can override model_id.")

    def _validate_file_count(self, files: list[AnalyzeFile]) -> None:
        if not files:
            raise ValidationError("At least one image is required.")
        max_files = self.settings.analyze_max_files_per_request
        if len(files) > max_files:
            raise ValidationError(f"At most {max_files} files per request.")

    def _validate_and_prepare(self, f: AnalyzeFile) -> _PreparedImage:
        allowed = self.settings.analyze_allowed_mime_types
        if f.content_type not in allowed:
            raise ValidationError(
                f"Unsupported content type {f.content_type!r}. Allowed: {', '.join(allowed)}."
            )

        max_bytes = self.settings.analyze_max_image_bytes
        size = len(f.data)
        if size > max_bytes:
            name = f.filename or "<unnamed>"
            raise ValidationError(f"File {name!r} exceeds max size of {max_bytes} bytes.")

        # PIL's ``verify`` consumes the buffer — re-open afterwards to
        # read width/height. Both opens use a fresh BytesIO so neither
        # leaves the buffer pointer in a dirty state.
        try:
            with Image.open(BytesIO(f.data)) as probe:
                probe.verify()
            with Image.open(BytesIO(f.data)) as probe2:
                width, height = probe2.size
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            name = f.filename or "<unnamed>"
            raise ValidationError(f"File {name!r} is not a valid image.") from exc

        return _PreparedImage(
            filename=f.filename,
            content_type=f.content_type,
            data=f.data,
            size_bytes=size,
            sha256=hashlib.sha256(f.data).hexdigest(),
            width=int(width),
            height=int(height),
        )

    def _build_batch(
        self,
        *,
        actor: AuthenticatedUser,
        supplier_id: UUID | None,
        gps_lat: Decimal | None,
        gps_long: Decimal | None,
        country_code: str | None,
        source: str | None = None,
    ) -> ScanBatch:
        location_source: str | None = None
        # The DB enforces ``(gps_lat IS NULL) = (gps_long IS NULL)``;
        # location_source is a hint about provenance.
        if gps_lat is not None or country_code is not None:
            location_source = LocationSource.MANUAL.value
        # Client-declared origin (web / mobile / mobile_realtime); defaults to
        # ``api`` for direct/SDK callers. An unknown value falls back to ``api``
        # rather than failing the scan.
        resolved_source = BatchSource.API.value
        if source is not None and source in BatchSource._value2member_map_:
            resolved_source = source
        return ScanBatch(
            id=uuid7(),
            user_id=actor.id,
            supplier_id=supplier_id,
            status=BatchStatus.PENDING.value,
            source=resolved_source,
            gps_lat=gps_lat,
            gps_long=gps_long,
            geo_country_code=country_code,
            location_source=location_source,
        )

    def _make_storage_key(self, batch_id: UUID, image_id: UUID, content_type: str) -> str:
        # Image id mirrors the row PK so the object path is trivially
        # traceable from a ``scan_images`` row to its MinIO object.
        ext = _MIME_TO_EXT.get(content_type, "")
        return f"batches/{batch_id}/{image_id}{ext}"


@dataclass(frozen=True, slots=True)
class _PreparedImage:
    """Validated, hashed, decoded — ready to write."""

    filename: str | None
    content_type: str
    data: bytes
    size_bytes: int
    sha256: str
    width: int
    height: int


__all__ = ["AnalysisService", "AnalyzeFile"]
