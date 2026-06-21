"""Inference backends.

Importing concrete backends (``torch_local``, ``roboflow``, ``ultralytics_yolo``)
requires the ``[inference]`` extra. The base Protocol + DTOs are torch-free
and safe to import everywhere.
"""

from seedbank.infrastructure.ml.backends.base import (
    BoundingBox,
    Classification,
    ClassificationConfig,
    Detection,
    DetectionConfig,
    InferenceBackend,
    InferenceResult,
)

__all__ = [
    "BoundingBox",
    "Classification",
    "ClassificationConfig",
    "Detection",
    "DetectionConfig",
    "InferenceBackend",
    "InferenceResult",
]
