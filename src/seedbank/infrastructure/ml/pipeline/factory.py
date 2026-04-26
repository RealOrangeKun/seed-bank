"""Pipeline + backend construction for worker-side and experiment-runner code.

The Celery worker and the (Phase 7) experiment runner both need a
``DetectPipeline`` and ``ClassifyPipeline`` wired up to the registered
backends. Centralising construction here keeps both consumers in lockstep
and gives us a single place to add a backend when one is registered.

Imports are deliberately lazy: importing this module must NOT pull torch
or ultralytics into the API process. The concrete backend modules are
imported inside the factory functions.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from seedbank.infrastructure.ml.backends.roboflow import RoboflowBackend
from seedbank.infrastructure.ml.backends.torch_local import TorchLocalBackend
from seedbank.infrastructure.ml.backends.ultralytics_yolo import (
    UltralyticsYoloBackend,
)
from seedbank.infrastructure.ml.manager import ModelManager
from seedbank.infrastructure.ml.pipeline.classify import ClassifyPipeline
from seedbank.infrastructure.ml.pipeline.detect import DetectPipeline

if TYPE_CHECKING:
    from seedbank.infrastructure.ml.backends.base import InferenceBackend


@lru_cache(maxsize=1)
def get_model_manager() -> ModelManager:
    """One ``ModelManager`` per process. Workers run with
    ``worker_prefetch_multiplier=1`` so a single manager backs every task."""
    return ModelManager()


def _build_backends(manager: ModelManager) -> dict[str, InferenceBackend]:
    """Instantiate every registered backend bound to the shared manager.

    Heavy imports (torch, ultralytics, inference-sdk) live inside each
    backend's method bodies, so importing this module is cheap.
    """
    return {
        "torch_local": TorchLocalBackend(manager),
        "yolo": UltralyticsYoloBackend(manager),
        "roboflow": RoboflowBackend(),
    }


def build_detect_pipeline() -> DetectPipeline:
    return DetectPipeline(_build_backends(get_model_manager()))


def build_classify_pipeline() -> ClassifyPipeline:
    return ClassifyPipeline(_build_backends(get_model_manager()))


__all__ = [
    "build_classify_pipeline",
    "build_detect_pipeline",
    "get_model_manager",
]
