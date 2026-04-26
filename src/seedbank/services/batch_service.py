"""Batch query service — read-only side of ``/api/v1/batches``.

Split from :class:`AnalysisService` deliberately: writing a batch
(multipart upload, MinIO, Celery dispatch) and reading one (eager-load
the nested graph) have nothing in common. Two thin services beat one
god class with two unrelated halves.

The service raises domain exceptions only — the router maps to HTTP.
``HTTPException`` is forbidden here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from seedbank.core.exceptions import NotFoundError
from seedbank.core.logging import get_logger
from seedbank.domain.user import Role

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from seedbank.domain.user import AuthenticatedUser
    from seedbank.infrastructure.db.models import ScanBatch
    from seedbank.infrastructure.db.repositories import ScanBatchRepository

log = get_logger(__name__)


class BatchService:
    """Read paths for ``ScanBatch`` aggregates."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        batches: ScanBatchRepository,
    ) -> None:
        self.session = session
        self.batches = batches

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        page: int,
        page_size: int,
        supplier_id: UUID | None = None,
        country_code: str | None = None,
    ) -> tuple[list[ScanBatch], int]:
        """Return ``(rows, total)`` for the requested page.

        ``total`` is the unpaginated count under the same filters so the
        caller can build a ``Page[BatchOut]``. ``page`` is 1-indexed,
        matching the schemas' :class:`PageMeta`.
        """
        offset = (page - 1) * page_size
        rows = await self.batches.list_for_user(
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
            row = await self.batches.get_with_images_and_detections(
                batch_id, actor.id
            )
        if row is None:
            raise NotFoundError("Batch not found.")
        return row


__all__ = ["BatchService"]
