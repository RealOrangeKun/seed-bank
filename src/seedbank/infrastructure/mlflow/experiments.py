"""MLflow helpers for the experiment runner.

Thin wrapper around :class:`MLflowAdapter` that the Celery task calls.
Splitting it out keeps the worker testable: tests monkeypatch this
module rather than the MLflow library itself.

All entry points are best-effort. A network blip on the MLflow box
should NOT fail an experiment whose metrics already landed in Postgres
and whose report is in MinIO. Failures are logged and swallowed; the
caller treats the absence of an ``mlflow_run_id`` as the signal.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import UUID

from seedbank.core.logging import get_logger
from seedbank.infrastructure.mlflow.client import get_mlflow

log = get_logger(__name__)


def start_run(
    *,
    experiment_id: UUID,
    experiment_name: str,
    model_id: UUID,
    dataset_id: UUID,
    kind: str,
) -> str | None:
    """Create an MLflow run; return its ``run_id`` or ``None`` on failure."""
    try:
        adapter = get_mlflow()
        return adapter.start_run(
            run_name=f"exp-{experiment_id}",
            tags={
                "seedbank.experiment_id": str(experiment_id),
                "seedbank.experiment_name": experiment_name,
                "seedbank.model_id": str(model_id),
                "seedbank.dataset_id": str(dataset_id),
                "seedbank.kind": kind,
            },
        )
    except Exception as exc:
        log.warning("mlflow.start_run_failed", error=repr(exc))
        return None


def log_run(
    *,
    run_id: str,
    params: dict[str, object],
    metrics: dict[str, float],
    report_markdown: str,
) -> None:
    """Log params + metrics + the rendered report as a run artifact.

    Each step is wrapped in its own try/except so a failure in one
    surface (e.g. artifact upload) doesn't lose the others.
    """
    try:
        adapter = get_mlflow()
        adapter.log_params(run_id, params)
    except Exception as exc:
        log.warning("mlflow.log_params_failed", run_id=run_id, error=repr(exc))

    try:
        adapter = get_mlflow()
        adapter.log_metrics(run_id, metrics)
    except Exception as exc:
        log.warning("mlflow.log_metrics_failed", run_id=run_id, error=repr(exc))

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "report.md"
            with report_path.open("w", encoding="utf-8") as f:
                f.write(report_markdown)
            adapter = get_mlflow()
            adapter.log_artifact(run_id, str(report_path))
    except Exception as exc:
        log.warning("mlflow.log_artifact_failed", run_id=run_id, error=repr(exc))


def terminate(run_id: str, *, status: str = "FINISHED") -> None:
    """Finalise the MLflow run. Status is one of MLflow's enum values:
    ``FINISHED`` | ``FAILED`` | ``KILLED``. Best-effort like the rest."""
    try:
        adapter = get_mlflow()
        adapter.set_terminated(run_id, status=status)
    except Exception as exc:
        log.warning("mlflow.terminate_failed", run_id=run_id, error=repr(exc))


__all__ = ["log_run", "start_run", "terminate"]
