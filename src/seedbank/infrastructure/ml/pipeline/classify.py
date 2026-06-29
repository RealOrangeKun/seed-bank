"""ClassifyPipeline — service-facing entry point for crop quality classification."""

from __future__ import annotations

import time
from dataclasses import dataclass

from seedbank.core.logging import get_logger
from seedbank.core.metrics import INFERENCE_DURATION, INFERENCE_TOTAL
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
        status = "ok"
        try:
            result = await backend.classify(crop, cfg)
        except Exception:
            status = "error"
            raise
        finally:
            elapsed = time.perf_counter() - start
            INFERENCE_DURATION.labels(kind="classification", backend=backend_name).observe(elapsed)
            INFERENCE_TOTAL.labels(kind="classification", backend=backend_name, status=status).inc()
        elapsed_ms = int(elapsed * 1000)
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

    async def run_batch(
        self,
        *,
        crops: list[bytes],
        cfg: ClassificationConfig,
        backend_name: str,
    ) -> list[ClassifyOutcome]:
        """Classify many crops against one model in a single backend call.

        Used by the two-stage worker to grade every seed crop from an image at
        once. Backends exposing ``classify_batch`` (torch_local) run a single
        batched forward pass; others fall back to sequential ``classify`` so the
        contract stays uniform. Metrics record one observation per crop so the
        per-crop latency distribution is unchanged versus the one-by-one path.
        """
        if not crops:
            return []
        backend = self._backends.get(backend_name)
        if backend is None:
            raise KeyError(
                f"No inference backend registered under '{backend_name}'. "
                f"Known: {sorted(self._backends)}"
            )

        batch_fn = getattr(backend, "classify_batch", None)
        start = time.perf_counter()
        status = "ok"
        try:
            if batch_fn is not None:
                results = await batch_fn(crops, cfg)
            else:
                results = [await backend.classify(c, cfg) for c in crops]
        except Exception:
            status = "error"
            raise
        finally:
            elapsed = time.perf_counter() - start
            for _ in crops:
                INFERENCE_DURATION.labels(
                    kind="classification", backend=backend_name
                ).observe(elapsed / len(crops))
                INFERENCE_TOTAL.labels(
                    kind="classification", backend=backend_name, status=status
                ).inc()

        # Spread the wall-clock cost evenly across crops for per-row bookkeeping.
        per_crop_ms = int(elapsed * 1000 / len(crops))
        return [
            ClassifyOutcome(
                classification=result,
                model_id=cfg.model_id,
                backend=backend_name,
                latency_ms=per_crop_ms,
            )
            for result in results
        ]


__all__ = ["ClassifyOutcome", "ClassifyPipeline"]
