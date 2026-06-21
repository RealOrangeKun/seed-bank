"""ScanImage repository.

The base class already provides ``add`` and ``get``. This subclass adds
the batch-scoped queries the analyze + batches code paths need.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select

from seedbank.infrastructure.db.models import ScanImage

from .base import Repository

if TYPE_CHECKING:
    from uuid import UUID


class ScanImageRepository(Repository[ScanImage]):
    model = ScanImage

    async def list_for_batch(self, batch_id: UUID) -> list[ScanImage]:
        """All images in a batch, ordered by upload time then id (stable)."""
        stmt = (
            select(ScanImage)
            .where(ScanImage.batch_id == batch_id)
            .order_by(ScanImage.uploaded_at, ScanImage.id)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_for_batch(self, batch_id: UUID) -> int:
        """Number of images attached to a batch."""
        stmt = select(func.count()).select_from(ScanImage).where(ScanImage.batch_id == batch_id)
        return int((await self.session.execute(stmt)).scalar_one())
