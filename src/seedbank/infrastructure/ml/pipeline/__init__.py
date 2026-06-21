"""Inference pipelines — thin orchestrators that call a backend and return
detection / classification outcomes plus the metadata services need to
write inference rows."""

from seedbank.infrastructure.ml.pipeline.classify import (
    ClassifyOutcome,
    ClassifyPipeline,
)
from seedbank.infrastructure.ml.pipeline.detect import (
    DetectOutcome,
    DetectPipeline,
)

__all__ = [
    "ClassifyOutcome",
    "ClassifyPipeline",
    "DetectOutcome",
    "DetectPipeline",
]
