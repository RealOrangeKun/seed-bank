"""Pydantic v2 DTOs for the model registry endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from seedbank.infrastructure.db.enums import ModelBackend, ModelKind, ModelStatus

# ── model_artifacts ─────────────────────────────────────────────────────────


class ModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    version: str
    kind: ModelKind
    backend: ModelBackend
    seed_type_id: UUID | None = None
    artifact_uri: str
    config: dict[str, Any] | None = None
    training_metadata: dict[str, Any] | None = None
    status: ModelStatus
    created_by: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ModelRegisterIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=160)]
    version: Annotated[str, Field(min_length=1, max_length=32)]
    kind: ModelKind
    backend: ModelBackend
    artifact_uri: Annotated[str, Field(min_length=1, max_length=512)]
    seed_type_id: UUID | None = None
    config: dict[str, Any] | None = None
    training_metadata: dict[str, Any] | None = None


class ModelStatusUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ModelStatus


class OfflineMetricOut(BaseModel):
    """One row from ``model_metrics`` — an offline-eval summary metric."""

    model_config = ConfigDict(from_attributes=True)

    metric_name: str
    metric_value: float
    dataset_id: UUID | None = None
    computed_at: datetime


class ModelPerformanceOut(BaseModel):
    """Aggregated performance for one model.

    ``offline_metrics`` come from Postgres ``model_metrics`` (Phase 7
    experiment runner upserts them). ``rows`` come from ClickHouse fact
    tables (Phase 8); until that table exists the field is empty and
    ``note`` carries a human-readable degradation reason.
    """

    model_config = ConfigDict(protected_namespaces=())

    model_id: UUID
    offline_metrics: list[OfflineMetricOut] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    note: str | None = None


__all__ = [
    "ModelOut",
    "ModelPerformanceOut",
    "ModelRegisterIn",
    "ModelStatusUpdateIn",
    "OfflineMetricOut",
]
