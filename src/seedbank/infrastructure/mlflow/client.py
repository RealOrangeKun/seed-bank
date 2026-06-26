"""MLflow tracking client.

Used by the experiment runner (Phase 7) and the model registry. The MLflow
client is sync; we keep it that way and wrap via `asyncio.to_thread` only
where called from the request path.

Heavy MLflow usage lives in Celery workers, where sync is fine.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import mlflow
from mlflow.tracking import MlflowClient

from seedbank.core.config import Settings, get_settings
from seedbank.core.logging import get_logger

log = get_logger(__name__)


class MLflowAdapter:
    """Convenience wrapper around `MlflowClient` for the patterns we use."""

    def __init__(self, client: MlflowClient, default_experiment: str) -> None:
        self._client = client
        self._default_experiment = default_experiment

    @classmethod
    def from_settings(cls, settings: Settings) -> MLflowAdapter:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        return cls(MlflowClient(settings.mlflow_tracking_uri), settings.mlflow_experiment_name)

    def ensure_experiment(self) -> str:
        """Return the experiment id, creating it if necessary."""
        exp = self._client.get_experiment_by_name(self._default_experiment)
        if exp is None:
            return self._client.create_experiment(self._default_experiment)
        experiment_id: str = exp.experiment_id
        return experiment_id

    def start_run(self, run_name: str, tags: dict[str, str] | None = None) -> str:
        exp_id = self.ensure_experiment()
        run = self._client.create_run(exp_id, tags=tags or {}, run_name=run_name)
        run_id: str = run.info.run_id
        return run_id

    def log_params(self, run_id: str, params: dict[str, Any]) -> None:
        for k, v in params.items():
            self._client.log_param(run_id, k, str(v))

    def log_metrics(self, run_id: str, metrics: dict[str, float], step: int = 0) -> None:
        for k, v in metrics.items():
            self._client.log_metric(run_id, k, v, step=step)

    def log_artifact(self, run_id: str, local_path: str) -> None:
        self._client.log_artifact(run_id, local_path)

    def set_terminated(self, run_id: str, status: str = "FINISHED") -> None:
        self._client.set_terminated(run_id, status=status)


@lru_cache(maxsize=1)
def get_mlflow() -> MLflowAdapter:
    return MLflowAdapter.from_settings(get_settings())
