"""DetectPipeline — service-facing entry point for object detection.

Pipelines are deliberately thin: pick a model via the traffic router, ask
the matching backend to detect, return the detections + the metadata
(``model_id``, ``backend``, ``latency_ms``) the calling service needs to
write the ``inferences`` row.

The DB write happens in ``services/analysis_service.py`` (Phase 6).
The pipeline never touches the session directly — that keeps it reusable
from the Celery worker (which has its own session) and from the experiment
runner (which writes ``experiment_results`` instead of ``inferences``).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from seedbank.core.logging import get_logger
from seedbank.infrastructure.ml.backends.base import (
    Detection,
    DetectionConfig,
    InferenceBackend,
)

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class DetectOutcome:
    """What the pipeline returns to the caller."""

    detections: list[Detection]
    model_id: object  # UUID — typed loose to keep this module framework-free
    backend: str
    latency_ms: int


class DetectPipeline:
    """Routes detection calls to the right backend.

    Construction is cheap; one is created per request.
    """

    def __init__(self, backends: dict[str, InferenceBackend]) -> None:
        self._backends = backends

    async def run(
        self,
        *,
        image: bytes,
        cfg: DetectionConfig,
        backend_name: str,
    ) -> DetectOutcome:
        backend = self._backends.get(backend_name)
        if backend is None:
            raise KeyError(
                f"No inference backend registered under '{backend_name}'. "
                f"Known: {sorted(self._backends)}"
            )

        start = time.perf_counter()
        detections = await backend.detect(image, cfg)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        log.info(
            "ml.detect",
            model_id=str(cfg.model_id),
            backend=backend_name,
            n=len(detections),
            latency_ms=elapsed_ms,
        )
        return DetectOutcome(
            detections=detections,
            model_id=cfg.model_id,
            backend=backend_name,
            latency_ms=elapsed_ms,
        )


__all__ = ["DetectOutcome", "DetectPipeline"]
