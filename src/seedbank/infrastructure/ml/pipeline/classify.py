"""ClassifyPipeline — service-facing entry point for crop quality classification."""

from __future__ import annotations

import time
from dataclasses import dataclass

from seedbank.core.logging import get_logger
from seedbank.infrastructure.ml.backends.base import (
    Classification,
    ClassificationConfig,
    InferenceBackend,
)

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ClassifyOutcome:
    classification: Classification
    model_id: object  # UUID
    backend: str
    latency_ms: int


class ClassifyPipeline:
    def __init__(self, backends: dict[str, InferenceBackend]) -> None:
        self._backends = backends

    async def run(
        self,
        *,
        crop: bytes,
        cfg: ClassificationConfig,
        backend_name: str,
    ) -> ClassifyOutcome:
        backend = self._backends.get(backend_name)
        if backend is None:
            raise KeyError(
                f"No inference backend registered under '{backend_name}'. "
                f"Known: {sorted(self._backends)}"
            )
        start = time.perf_counter()
        result = await backend.classify(crop, cfg)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        log.info(
            "ml.classify",
            model_id=str(cfg.model_id),
            backend=backend_name,
            label=result.label,
            confidence=result.confidence,
            latency_ms=elapsed_ms,
        )
        return ClassifyOutcome(
            classification=result,
            model_id=cfg.model_id,
            backend=backend_name,
            latency_ms=elapsed_ms,
        )


__all__ = ["ClassifyOutcome", "ClassifyPipeline"]
