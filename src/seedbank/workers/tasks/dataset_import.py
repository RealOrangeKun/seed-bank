"""``seedbank.import_yolo_dataset`` — unpack a YOLO ``.zip`` into dataset items.

The API stores the uploaded archive in MinIO ``seedbank-datasets`` and
dispatches this task on the CPU queue (no torch needed — this only unpacks the
archive, writes images, and inserts rows). For each image it uploads the bytes
under a server-chosen key and appends one ``dataset_items`` row whose
``ground_truth`` is the canonical detection shape
(``{"kind": "detection", "boxes": [...]}``) that the experiment runner already
understands. Images are written to MinIO **before** the DB commit, so committed
rows always reference reachable objects (same invariant as the analyze path).
The staging archive is removed on success.

A single ``.txt`` label with no matching image is ignored; an image with no
label (or an empty label) becomes a background item with no boxes.
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import os
import posixpath
import tempfile
from pathlib import Path
from uuid import UUID

from seedbank.core.config import get_settings
from seedbank.core.exceptions import ExternalServiceError, NotFoundError
from seedbank.core.ids import uuid7
from seedbank.core.logging import get_logger
from seedbank.infrastructure.db.models import DatasetItem
from seedbank.infrastructure.db.repositories import (
    DatasetItemRepository,
    DatasetRepository,
)
from seedbank.infrastructure.storage import get_storage
from seedbank.services.dataset_import import (
    YoloArchiveEntry,
    open_yolo_archive,
    plan_yolo_archive,
)
from seedbank.workers.celery_app import celery_app
from seedbank.workers.runtime import run_async
from seedbank.workers.session import worker_session_scope

log = get_logger(__name__)

_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


@celery_app.task(  # type: ignore[untyped-decorator]
    name="seedbank.import_yolo_dataset",
    bind=True,
    max_retries=1,
    default_retry_delay=10,
    autoretry_for=(ExternalServiceError,),
)
def import_yolo_dataset(
    self: object,  # noqa: ARG001 — Celery requires bind=True to accept self
    dataset_id: str,
    zip_storage_key: str,
) -> None:
    """Sync wrapper. Real work in the async coroutine."""
    run_async(
        _async_import(dataset_id=UUID(dataset_id), zip_storage_key=zip_storage_key),
    )


async def _async_import(*, dataset_id: UUID, zip_storage_key: str) -> None:
    settings = get_settings()
    storage = get_storage()
    bucket = settings.minio_bucket_datasets

    imported = 0
    skipped = 0
    empty_labels = 0
    rows: list[DatasetItem] = []

    # Stream the archive to a temp file so a large dataset never sits in worker
    # RAM (worker-cpu is memory-capped), then read one image at a time.
    fd, tmp_path = tempfile.mkstemp(suffix=".zip", prefix="yolo-import-")
    os.close(fd)
    try:
        await storage.download_to_file(bucket, zip_storage_key, tmp_path)

        with open_yolo_archive(tmp_path) as zf:
            # Pairing + label parsing is blocking work — keep it off the loop.
            entries: list[YoloArchiveEntry] = await asyncio.to_thread(
                plan_yolo_archive,
                zf,
                max_uncompressed_bytes=settings.dataset_import_max_zip_bytes,
                max_items=settings.dataset_import_max_items,
                image_extensions=settings.dataset_import_image_extensions,
            )

            for entry in entries:
                # Read + decode-check one image at a time (bounded memory).
                image_bytes = await asyncio.to_thread(zf.read, entry.member_name)
                if not await asyncio.to_thread(_is_valid_image, image_bytes):
                    skipped += 1
                    continue
                suffix = posixpath.splitext(entry.filename)[1].lower()
                key = f"datasets/{dataset_id}/{uuid7()}{suffix}"
                await storage.put_object(
                    bucket,
                    key,
                    image_bytes,
                    _CONTENT_TYPES.get(suffix, "application/octet-stream"),
                )
                if not entry.boxes:
                    empty_labels += 1
                rows.append(
                    DatasetItem(
                        id=uuid7(),
                        dataset_id=dataset_id,
                        image_storage_key=key,
                        ground_truth={"kind": "detection", "boxes": entry.boxes},
                    )
                )
                imported += 1
    finally:
        await asyncio.to_thread(_remove_file, tmp_path)

    async with worker_session_scope() as session:
        datasets = DatasetRepository(session)
        item_repo = DatasetItemRepository(session)

        dataset = await datasets.get_active(dataset_id)
        if dataset is None:
            raise NotFoundError(f"dataset {dataset_id} not found")

        if rows:
            await item_repo.add_many(rows)
            await session.commit()

    # Best-effort cleanup of the staging archive — a leftover zip is harmless.
    try:
        await storage.remove_object(bucket, zip_storage_key)
    except ExternalServiceError as exc:
        log.warning(
            "dataset.import_cleanup_failed",
            dataset_id=str(dataset_id),
            zip_storage_key=zip_storage_key,
            error=repr(exc),
        )

    log.info(
        "dataset.import_completed",
        dataset_id=str(dataset_id),
        imported=imported,
        skipped=skipped,
        empty_labels=empty_labels,
    )


def _remove_file(path: str) -> None:
    """Delete a temp file, ignoring a missing/locked one (best-effort cleanup)."""
    with contextlib.suppress(OSError):
        Path(path).unlink()


def _is_valid_image(data: bytes) -> bool:
    """Decode-check image bytes with Pillow; skip anything that won't open."""
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        return False
    return True


__all__ = ["import_yolo_dataset"]
