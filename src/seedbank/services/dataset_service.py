"""Dataset service — registry use cases for the eval substrate.

The service owns:

- Creating a dataset (unique name; conflict translated to
  :class:`ConflictError`).
- Bulk-adding items (uniqueness on ``(dataset_id, image_storage_key)``).
- Listing/reading datasets and their items.
- Soft-deleting an unused dataset.

Authorization is handled by the router via ``require_role(AI_DEVELOPER)``;
admins implicitly satisfy the check. The service raises domain errors only.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError

from seedbank.core.config import get_settings
from seedbank.core.exceptions import ConflictError, NotFoundError, ValidationError
from seedbank.core.ids import uuid7
from seedbank.core.logging import get_logger
from seedbank.infrastructure.db.models import Dataset, DatasetItem
from seedbank.infrastructure.storage import get_storage
from seedbank.workers.celery_app import celery_app

# The YOLO import task runs on the CPU worker (no torch): it only unpacks the
# archive, writes images to MinIO, and inserts rows.
_IMPORT_TASK_NAME = "seedbank.import_yolo_dataset"
_IMPORT_TASK_QUEUE = "default"

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from seedbank.core.config import Settings
    from seedbank.domain.user import AuthenticatedUser
    from seedbank.infrastructure.db.repositories import (
        DatasetItemRepository,
        DatasetRepository,
    )
    from seedbank.infrastructure.storage import MinioStorage
    from seedbank.schemas.dataset import DatasetItemCreateIn

log = get_logger(__name__)


class DatasetService:
    """Use cases for ``/api/v1/datasets``."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        datasets: DatasetRepository,
        items: DatasetItemRepository,
        storage: MinioStorage | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.datasets = datasets
        self.items = items
        # Storage + settings are only needed to mint presigned upload URLs;
        # they default to the singletons so existing callers (and the unit
        # tests that build the service with mocked repos) keep working.
        self.storage = storage or get_storage()
        self.settings = settings or get_settings()

    async def create(
        self,
        *,
        actor: AuthenticatedUser,
        name: str,
        description: str | None,
    ) -> Dataset:
        """Create a dataset. Unique-name violation → :class:`ConflictError`."""
        existing = await self.datasets.get_by_name(name)
        if existing is not None:
            raise ConflictError(f"Dataset name {name!r} already exists.")
        dataset = Dataset(
            id=uuid7(),
            name=name,
            description=description,
            created_by=actor.id,
        )
        try:
            await self.datasets.add(dataset)
            await self.session.commit()
        except IntegrityError as exc:
            # Race: someone else inserted the same name between get_by_name
            # and add. Translate cleanly so the router returns 409.
            await self.session.rollback()
            raise ConflictError(f"Dataset name {name!r} already exists.") from exc
        log.info(
            "dataset.created",
            dataset_id=str(dataset.id),
            name=name,
            actor_id=str(actor.id),
        )
        return dataset

    async def get(self, dataset_id: UUID) -> Dataset:
        """Return an active dataset or raise :class:`NotFoundError`."""
        dataset = await self.datasets.get_active(dataset_id)
        if dataset is None:
            raise NotFoundError("Dataset not found.")
        return dataset

    async def list_with_counts(
        self,
        *,
        page: int,
        page_size: int,
    ) -> tuple[list[tuple[Dataset, int]], int]:
        """List datasets paginated, each annotated with its current
        ``item_count``. ``total`` is the unfiltered count of active datasets.
        """
        offset = (page - 1) * page_size
        rows = await self.datasets.list_active(limit=page_size, offset=offset)
        total = await self.datasets.count_active()
        # One COUNT per dataset on the page is fine at MVP scale (page_size
        # ≤ 200). If it ever hurts, swap to a single grouped query.
        annotated: list[tuple[Dataset, int]] = []
        for ds in rows:
            cnt = await self.items.count_for_dataset(ds.id)
            annotated.append((ds, cnt))
        return annotated, total

    async def get_with_count(self, dataset_id: UUID) -> tuple[Dataset, int]:
        ds = await self.get(dataset_id)
        cnt = await self.items.count_for_dataset(ds.id)
        return ds, cnt

    async def create_upload_url(
        self,
        *,
        dataset_id: UUID,
        filename: str,
        content_type: str,
    ) -> tuple[str, str]:
        """Mint a short-lived presigned PUT URL for one dataset image.

        Returns ``(upload_url, storage_key)``. The browser PUTs the bytes
        straight to MinIO (they never traverse the API), then registers the
        item via ``POST /datasets/{id}/items`` with the returned key. The key
        is server-chosen (``datasets/{dataset_id}/{uuid7}{ext}``) so two
        uploads of the same filename never collide; only the extension is
        taken from ``filename``. Raises :class:`NotFoundError` if the dataset
        isn't active.
        """
        ds = await self.datasets.get_active(dataset_id)
        if ds is None:
            raise NotFoundError("Dataset not found.")

        suffix = Path(filename).suffix.lower()
        key = f"datasets/{ds.id}/{uuid7()}{suffix}"
        ttl = timedelta(seconds=self.settings.minio_presign_ttl_seconds)
        url = await self.storage.presigned_put_url(
            self.settings.minio_bucket_datasets,
            key,
            ttl,
            content_type=content_type,
        )
        log.info("dataset.upload_url_minted", dataset_id=str(ds.id), storage_key=key)
        return url, key

    async def dispatch_yolo_import(
        self,
        *,
        dataset_id: UUID,
        zip_storage_key: str,
    ) -> None:
        """Kick off a background YOLO import for a previously-uploaded ``.zip``.

        The archive must already be in MinIO ``seedbank-datasets`` (via a
        presigned PUT). We verify the dataset is active and the object exists,
        then dispatch the CPU worker task that unpacks it. Raises
        :class:`NotFoundError` if the dataset is gone and
        :class:`ValidationError` if the archive object is missing.
        """
        ds = await self.datasets.get_active(dataset_id)
        if ds is None:
            raise NotFoundError("Dataset not found.")

        exists = await self.storage.object_exists(
            self.settings.minio_bucket_datasets, zip_storage_key
        )
        if not exists:
            raise ValidationError("Uploaded archive not found; upload it before importing.")

        celery_app.send_task(
            _IMPORT_TASK_NAME,
            args=[str(ds.id), zip_storage_key],
            queue=_IMPORT_TASK_QUEUE,
        )
        log.info(
            "dataset.import_dispatched",
            dataset_id=str(ds.id),
            zip_storage_key=zip_storage_key,
        )

    async def add_items(
        self,
        *,
        dataset_id: UUID,
        items: list[DatasetItemCreateIn],
    ) -> int:
        """Bulk-append items. Returns count added.

        Uniqueness is on ``(dataset_id, image_storage_key)``; duplicates
        within the dataset translate to :class:`ConflictError`. The
        whole batch is atomic — partial inserts would make manifests
        non-reproducible.
        """
        ds = await self.datasets.get_active(dataset_id)
        if ds is None:
            raise NotFoundError("Dataset not found.")

        # Detect intra-payload duplicates up-front so we don't waste an
        # IntegrityError round-trip and we can give a precise error.
        keys = [it.image_storage_key for it in items]
        if len(keys) != len(set(keys)):
            raise ConflictError("Duplicate image_storage_key within request payload.")

        rows = [
            DatasetItem(
                id=uuid7(),
                dataset_id=ds.id,
                image_storage_key=it.image_storage_key,
                ground_truth=it.ground_truth,
                checksum=it.checksum,
            )
            for it in items
        ]
        try:
            await self.items.add_many(rows)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(
                "One or more image_storage_key values already exist in this dataset."
            ) from exc
        log.info(
            "dataset.items_added",
            dataset_id=str(ds.id),
            n=len(rows),
        )
        return len(rows)

    async def list_items(
        self,
        *,
        dataset_id: UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[DatasetItem], int]:
        ds = await self.datasets.get_active(dataset_id)
        if ds is None:
            raise NotFoundError("Dataset not found.")
        offset = (page - 1) * page_size
        rows = await self.items.list_for_dataset(ds.id, limit=page_size, offset=offset)
        total = await self.items.count_for_dataset(ds.id)
        return rows, total


__all__ = ["DatasetService"]
