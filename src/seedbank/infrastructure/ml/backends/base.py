"""``InferenceBackend`` Protocol + framework-free DTOs.

Routers/services depend on the protocol; concrete backends (torch_local,
roboflow, ultralytics_yolo) implement it. Adding a new backend is a matter
of writing a class whose method signatures match — no inheritance required.

Detection / Classification dataclasses are deliberately framework-free so
they can travel through the layered architecture without dragging torch
or numpy with them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable
from uuid import UUID


# ── DTOs ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Normalized [0, 1] bounding box. The platform stores normalized coords
    as the source of truth; pixel coords are derived at render time."""

    x: float
    y: float
    w: float
    h: float


@dataclass(frozen=True, slots=True)
class Detection:
    """One detected object."""

    bbox: BoundingBox
    class_id: int
    class_name: str | None
    confidence: float


@dataclass(frozen=True, slots=True)
class Classification:
    """One classified crop."""

    label: str  # e.g. "good" | "bad"
    confidence: float
    raw_score: float | None = None  # post-sigmoid logit, useful for calibration


@dataclass(frozen=True, slots=True)
class DetectionConfig:
    """Per-call knobs for a detection backend."""

    model_id: UUID
    artifact_uri: str
    builder_key: str  # registry key for torch_local; ignored by hosted backends
    confidence_threshold: float = 0.5
    iou_threshold: float = 0.5
    max_detections: int = 300
    image_size: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ClassificationConfig:
    """Per-call knobs for a classifier backend."""

    model_id: UUID
    artifact_uri: str
    builder_key: str
    threshold: float = 0.5
    image_size: int = 224
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class InferenceResult:
    """Common envelope returned by pipelines: detections/classification +
    metadata the caller needs to write the ``inferences`` row."""

    model_id: UUID
    backend: str
    latency_ms: int


# ── Protocol ─────────────────────────────────────────────────────────────────


@runtime_checkable
class InferenceBackend(Protocol):
    """The contract every backend satisfies. Methods are async because some
    backends (Roboflow) are network-bound and even local torch inference
    can be offloaded to a thread to keep the event loop responsive."""

    name: str  # matches `model_backend` enum: "torch_local" | "roboflow" | "yolo"

    async def detect(self, image: bytes, cfg: DetectionConfig) -> list[Detection]: ...

    async def classify(self, crop: bytes, cfg: ClassificationConfig) -> Classification: ...


__all__ = [
    "BoundingBox",
    "Classification",
    "ClassificationConfig",
    "Detection",
    "DetectionConfig",
    "InferenceBackend",
    "InferenceResult",
]
