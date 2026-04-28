"""Dataset + DatasetItem repositories.

Datasets are the eval substrate: a frozen list of images with ground-truth
annotations (boxes for detection, label for classification). They are
immutable from an experiment's point of view — appending items invalidates
no past experiment because each ``ExperimentResult`` carries
``dataset_item_id`` so historical comparisons stay reproducible.

Soft-delete only on :class:`Dataset` (user-visible aggregate). Items hard-
cascade with the dataset; partial item deletes are not part of the API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import desc, func, select

from seedbank.core.logging import get_logger
from seedbank.infrastructure.db.models import Dataset, DatasetItem

from .base import Repository

if TYPE_CHECKING:
    from uuid import UUID


log = get_logger(__name__)


class DatasetRepository(Repository[Dataset]):
    model = Dataset

    async def get_active(self, dataset_id: UUID) -> Dataset | None:
        """Soft-delete-aware fetch."""
        stmt = select(Dataset).where(
            Dataset.id == dataset_id,
            Dataset.deleted_at.is_(None),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_name(self, name: str) -> Dataset | None:
        stmt = select(Dataset).where(
            Dataset.name == name,
            Dataset.deleted_at.is_(None),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_active(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        created_by: UUID | None = None,
    ) -> list[Dataset]:
        stmt = select(Dataset).where(Dataset.deleted_at.is_(None))
        if created_by is not None:
            stmt = stmt.where(Dataset.created_by == created_by)
        stmt = stmt.order_by(desc(Dataset.created_at)).limit(limit).offset(offset)
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_active(self, *, created_by: UUID | None = None) -> int:
        stmt = select(func.count()).select_from(Dataset).where(Dataset.deleted_at.is_(None))
        if created_by is not None:
            stmt = stmt.where(Dataset.created_by == created_by)
        return int((await self.session.execute(stmt)).scalar_one())


class DatasetItemRepository(Repository[DatasetItem]):
    model = DatasetItem

    async def add_many(self, rows: list[DatasetItem]) -> None:
        """Bulk-insert items. Uniqueness violations bubble up as
        :class:`sqlalchemy.exc.IntegrityError` for the service to translate."""
        if not rows:
            return
        self.session.add_all(rows)
        await self.session.flush()

    async def list_for_dataset(
        self, dataset_id: UUID, *, limit: int = 50, offset: int = 0
    ) -> list[DatasetItem]:
        stmt = (
            select(DatasetItem)
            .where(DatasetItem.dataset_id == dataset_id)
            .order_by(DatasetItem.id)
            .limit(limit)
            .offset(offset)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_for_dataset(self, dataset_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(DatasetItem)
            .where(DatasetItem.dataset_id == dataset_id)
        )
        return int((await self.session.execute(stmt)).scalar_one())
