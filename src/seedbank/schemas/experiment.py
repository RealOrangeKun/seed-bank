"""Pydantic shapes for ``/api/v1/experiments``.

An experiment is a single offline evaluation: take one ``ModelArtifact``,
run it against one frozen ``Dataset``, write per-item results plus
summary metrics. The detail response wraps the summary; the
per-item rows have their own paginated endpoint.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from seedbank.infrastructure.db.enums import ExperimentStatus

# ``model_*`` fields collide with Pydantic's protected namespaces; opt out
# at the class level so the schema generator stays quiet. Request bodies are
# also strict (reject typo'd keys), so the input config carries both flags.
_STRICT_ALLOW_MODEL_PREFIX = ConfigDict(extra="forbid", protected_namespaces=())


class ExperimentCreateIn(BaseModel):
    """Request body for ``POST /experiments``.

    ``name`` is human-readable; ``model_id`` and ``dataset_id`` are the
    only required references. The worker resolves both during dispatch.
    """

    model_config = _STRICT_ALLOW_MODEL_PREFIX

    name: str = Field(min_length=1, max_length=160)
    model_id: UUID
    dataset_id: UUID


class ExperimentSummaryOut(BaseModel):
    """List-row + create-response shape — small enough to ship in lists."""

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID
    name: str
    status: ExperimentStatus
    model_id: UUID
    dataset_id: UUID
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    summary_metrics: dict[str, Any] | None = None
    created_at: datetime
    created_by: UUID | None = None


class ExperimentResultOut(BaseModel):
    """Per-item entry in the paginated results listing."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_item_id: UUID
    predicted_boxes: dict[str, Any] | None = None
    latency_ms: int | None = None
    error: str | None = None


class ExperimentDetailOut(ExperimentSummaryOut):
    """Detail view — same as summary plus the embedded result count."""

    result_count: int = 0


__all__ = [
    "ExperimentCreateIn",
    "ExperimentDetailOut",
    "ExperimentResultOut",
    "ExperimentSummaryOut",
]
