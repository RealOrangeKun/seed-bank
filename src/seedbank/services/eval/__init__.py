"""Offline-evaluation helpers used by the experiment runner.

Pure functions, no IO, no SQLAlchemy. The Celery task in
:mod:`seedbank.workers.tasks.experiment` orchestrates IO and calls these
to compute per-item and aggregate metrics.
"""

from .classification import (
    ClassificationAggregate,
    ClassificationItemResult,
    aggregate_classification,
    evaluate_classification_item,
)
from .detection import (
    DetectionAggregate,
    DetectionItemMetrics,
    GroundTruthBox,
    aggregate_detection,
    evaluate_detection_item,
    iou,
)
from .report import render_report

__all__ = [
    "ClassificationAggregate",
    "ClassificationItemResult",
    "DetectionAggregate",
    "DetectionItemMetrics",
    "GroundTruthBox",
    "aggregate_classification",
    "aggregate_detection",
    "evaluate_classification_item",
    "evaluate_detection_item",
    "iou",
    "render_report",
]
