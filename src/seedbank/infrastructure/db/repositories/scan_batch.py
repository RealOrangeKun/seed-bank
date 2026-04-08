"""ScanBatch repository — batches, their images, and the inferences/detections
joined under each."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload

from seedbank.infrastructure.db.models import (
    Inference,
    ScanBatch,
    ScanImage,
    SeedDetection,
)

from .base import Repository


class ScanBatchRepository(Repository[ScanBatch]):
    model = ScanBatch

    async def get_for_user(self, batch_id: UUID, user_id: UUID) -> ScanBatch | None:
        """Fetch a batch the caller owns. Soft-deleted rows excluded."""
        stmt = select(ScanBatch).where(
            ScanBatch.id == batch_id,
            ScanBatch.user_id == user_id,
            ScanBatch.deleted_at.is_(None),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
        supplier_id: UUID | None = None,
        country_code: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[ScanBatch]:
        stmt = select(ScanBatch).where(
            ScanBatch.user_id == user_id,
            ScanBatch.deleted_at.is_(None),
        )
        if supplier_id is not None:
            stmt = stmt.where(ScanBatch.supplier_id == supplier_id)
        if country_code is not None:
            stmt = stmt.where(ScanBatch.geo_country_code == country_code)
        if since is not None:
            stmt = stmt.where(ScanBatch.submitted_at >= since)
        if until is not None:
            stmt = stmt.where(ScanBatch.submitted_at <= until)

        stmt = stmt.order_by(desc(ScanBatch.submitted_at)).limit(limit).offset(offset)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_with_images_and_detections(
        self, batch_id: UUID, user_id: UUID
    ) -> ScanBatch | None:
        """Eager-load images → inferences → detections for the batch detail
        view. Uses `selectinload` so each level is one extra query, not an N+1."""
        stmt = (
            select(ScanBatch)
            .where(
                ScanBatch.id == batch_id,
                ScanBatch.user_id == user_id,
                ScanBatch.deleted_at.is_(None),
            )
            .options(
                selectinload(ScanBatch.images)
                .selectinload(ScanImage.inferences)
                .selectinload(Inference.detections)
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_detections_for_batch(
        self, batch_id: UUID, user_id: UUID
    ) -> list[SeedDetection]:
        """Flat list of every detection across the batch's images + models."""
        stmt = (
            select(SeedDetection)
            .join(Inference, SeedDetection.inference_id == Inference.id)
            .join(ScanImage, Inference.image_id == ScanImage.id)
            .join(ScanBatch, ScanImage.batch_id == ScanBatch.id)
            .where(
                ScanBatch.id == batch_id,
                ScanBatch.user_id == user_id,
                ScanBatch.deleted_at.is_(None),
            )
        )
        return list((await self.session.execute(stmt)).scalars().all())
