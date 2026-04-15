"""Pydantic stubs for the experiment endpoints (Phase 7).

Filled out here only enough for ``schemas.__init__`` re-exports and so the
ML-platform endpoints can refer to ``ExperimentSummaryOut`` if needed. The
actual experiment service lands in Phase 7.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from seedbank.infrastructure.db.enums import ExperimentStatus


class ExperimentSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    status: ExperimentStatus
    model_id: UUID
    dataset_id: UUID
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    summary_metrics: dict[str, Any] | None = None
    mlflow_run_id: str | None = None


__all__ = ["ExperimentSummaryOut"]
