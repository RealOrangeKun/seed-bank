"""Batch query service — read-only side of ``/api/v1/batches``.

Split from :class:`AnalysisService` deliberately: writing a batch
(multipart upload, MinIO, Celery dispatch) and reading one (eager-load
the nested graph) have nothing in common. Two thin services beat one
god class with two unrelated halves.

The service raises domain exceptions only — the router maps to HTTP.
``HTTPException`` is forbidden here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from seedbank.core.config import get_settings
from seedbank.core.exceptions import NotFoundError
from seedbank.core.logging import get_logger
from seedbank.domain.user import Role

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from seedbank.core.config import Settings
    from seedbank.domain.user import AuthenticatedUser
    from seedbank.infrastructure.db.models import ScanBatch
    from seedbank.infrastructure.db.repositories import (
        ScanBatchRepository,
        ScanImageRepository,
    )
    from seedbank.infrastructure.storage import MinioStorage

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ImageUrl:
    """A presigned, browser-reachable URL for one stored scan image."""

    image_id: UUID
    url: str
    expires_at: datetime


class BatchService:
    """Read paths for ``ScanBatch`` aggregates."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        batches: ScanBatchRepository,
        images: ScanImageRepository,
        storage: MinioStorage,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.batches = batches
        self.images = images
        self.storage = storage
        self.settings = settings or get_settings()

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        page: int,
        page_size: int,
        supplier_id: UUID | None = None,
        country_code: str | None = None,
    ) -> tuple[list[tuple[ScanBatch, int]], int]:
        """Return ``(rows, total)`` for the requested page.

        Each row is a ``(batch, image_count)`` pair — ``scan_batches`` has
        no ``image_count`` column, so the repository derives it in a single
        grouped query (no N+1). ``total`` is the unpaginated count under the
        same filters so the caller can build a ``Page[BatchOut]``. ``page``
        is 1-indexed, matching the schemas' :class:`PageMeta`.
        """
        offset = (page - 1) * page_size
        rows = await self.batches.list_for_user_with_counts(
            user_id,
            limit=page_size,
            offset=offset,
            supplier_id=supplier_id,
            country_code=country_code,
        )
        total = await self.batches.count_for_user(
            user_id,
            supplier_id=supplier_id,
            country_code=country_code,
        )
        return rows, total

    async def get_for_user(
        self,
        *,
        batch_id: UUID,
        actor: AuthenticatedUser,
    ) -> ScanBatch:
        """Fetch the full nested graph for a batch the actor may read.

        - Admins use the unscoped query and may read any batch.
        - Everyone else is filtered by ``user_id`` so a user cannot
          enumerate someone else's batches.

        ``NotFoundError`` is raised both when the row is absent and when
        a non-admin caller does not own it. Leaking the difference would
        let users probe for IDs.
        """
        if actor.role is Role.ADMIN:
            row = await self.batches.get_with_full_graph(batch_id)
        else:
            row = await self.batches.get_with_images_and_detections(batch_id, actor.id)
        if row is None:
            raise NotFoundError("Batch not found.")
        return row

    async def image_urls_for_user(
        self,
        *,
        batch_id: UUID,
        actor: AuthenticatedUser,
    ) -> list[ImageUrl]:
        """Presigned GET URLs for every image in a batch the actor may read.

        Ownership is enforced exactly as in :meth:`get_for_user` (admins may
        read any batch; everyone else only their own), and the same
        ``NotFoundError``-on-miss rule applies so image IDs cannot be probed.
        Unlike :meth:`get_for_user` this does *not* load the detection graph —
        only the lightweight image rows are needed to mint URLs.
        """
        if actor.role is Role.ADMIN:
            batch = await self.batches.get(batch_id)
        else:
            batch = await self.batches.get_for_user(batch_id, actor.id)
        if batch is None:
            raise NotFoundError("Batch not found.")

        ttl = timedelta(seconds=self.settings.minio_presign_ttl_seconds)
        expires_at = datetime.now(UTC) + ttl
        images = await self.images.list_for_batch(batch_id)
        urls: list[ImageUrl] = []
        for image in images:
            url = await self.storage.presigned_get_url(
                self.settings.minio_bucket_images, image.storage_key, ttl
            )
            urls.append(ImageUrl(image_id=image.id, url=url, expires_at=expires_at))
        return urls


__all__ = ["BatchService", "ImageUrl"]
