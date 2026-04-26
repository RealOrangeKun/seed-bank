"""Inference repository.

One row per ``(image, model)`` inference attempt. The ``model_id`` column
is the audit anchor — every detection joins back to the exact model
artifact that produced it (CLAUDE.md pillar 5).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import update

from seedbank.core.logging import get_logger
from seedbank.infrastructure.db.models import Inference

from .base import Repository

if TYPE_CHECKING:
    from uuid import UUID

log = get_logger(__name__)


class InferenceRepository(Repository[Inference]):
    model = Inference

    async def add_inference(
        self,
        *,
        image_id: UUID,
        model_id: UUID,
        backend: str,
        latency_ms: int | None,
        error: str | None = None,
    ) -> Inference:
        """Insert a single inference row and flush so the PK is assigned."""
        row = Inference(
            image_id=image_id,
            model_id=model_id,
            backend=backend,
            latency_ms=latency_ms,
            error=error,
        )
        self.session.add(row)
        await self.session.flush()
        log.info(
            "inference.added",
            inference_id=str(row.id),
            image_id=str(image_id),
            model_id=str(model_id),
            backend=backend,
            latency_ms=latency_ms,
            has_error=error is not None,
        )
        return row

    async def set_error(self, inference_id: UUID, error: str) -> int:
        """Record a terminal error against an existing inference row.

        Returns the affected row count (0 = no such id).
        """
        stmt = (
            update(Inference)
            .where(Inference.id == inference_id)
            .values(error=error)
        )
        result = await self.session.execute(stmt)
        rowcount = result.rowcount or 0
        log.info(
            "inference.set_error",
            inference_id=str(inference_id),
            rowcount=rowcount,
        )
        return rowcount
