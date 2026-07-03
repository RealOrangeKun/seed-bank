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
    COCO_IOU_THRESHOLDS,
    DetectionAggregate,
    DetectionItemMetrics,
    GroundTruthBox,
    aggregate_detection,
    average_precision,
    compute_map,
    evaluate_detection_item,
    iou,
)
from .report import render_report

__all__ = [
    "COCO_IOU_THRESHOLDS",
    "ClassificationAggregate",
    "ClassificationItemResult",
    "DetectionAggregate",
    "DetectionItemMetrics",
    "GroundTruthBox",
    "aggregate_classification",
    "aggregate_detection",
    "average_precision",
    "compute_map",
    "evaluate_classification_item",
    "evaluate_detection_item",
    "iou",
    "render_report",
]
