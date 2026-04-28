"""Detection eval — IoU matching + precision/recall/F1 aggregation.

Single-class for now (good seeds vs background). Multi-class mAP can be
layered on later by changing :func:`evaluate_detection_item` to bucket
matches by ``label`` before counting TP/FP/FN; the aggregation function
already accumulates additively so the changes stay local.

The matcher is greedy: predictions are sorted by descending confidence,
then each prediction is matched against the highest-IoU unmatched ground
truth box that exceeds the threshold. This is the standard PASCAL VOC
evaluation protocol at a single IoU value.

All metrics are returned as :class:`Decimal` because they live in
``model_metrics.metric_value NUMERIC(12, 6)``.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import Decimal

from seedbank.infrastructure.ml.backends.base import BoundingBox, Detection


@dataclass(frozen=True, slots=True)
class GroundTruthBox:
    """One annotated bounding box from a dataset item.

    ``label`` is preserved for forward compatibility with multi-class mAP;
    the MVP single-class evaluator ignores it.
    """

    x: float
    y: float
    w: float
    h: float
    label: str = "good"


def iou(pred: BoundingBox, gt: GroundTruthBox) -> float:
    """Intersection-over-union for two normalized boxes.

    Both inputs are in ``(x, y, w, h)`` form with all values in ``[0, 1]``;
    callers are responsible for clamping. Returns ``0.0`` when either box
    has non-positive area.
    """
    if pred.w <= 0 or pred.h <= 0 or gt.w <= 0 or gt.h <= 0:
        return 0.0

    px1, py1 = pred.x, pred.y
    px2, py2 = pred.x + pred.w, pred.y + pred.h
    gx1, gy1 = gt.x, gt.y
    gx2, gy2 = gt.x + gt.w, gt.y + gt.h

    ix1 = max(px1, gx1)
    iy1 = max(py1, gy1)
    ix2 = min(px2, gx2)
    iy2 = min(py2, gy2)

    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0.0:
        return 0.0

    pred_area = pred.w * pred.h
    gt_area = gt.w * gt.h
    union = pred_area + gt_area - inter
    if union <= 0.0:
        return 0.0
    return inter / union


@dataclass(slots=True)
class DetectionItemMetrics:
    """Per-item eval result before aggregation."""

    tp: int
    fp: int
    fn: int
    latency_ms: int
    matched_gt_indices: list[int] = field(default_factory=list)


def evaluate_detection_item(
    *,
    predictions: list[Detection],
    ground_truth: list[GroundTruthBox],
    latency_ms: int,
    iou_threshold: float = 0.5,
) -> DetectionItemMetrics:
    """Greedy IoU matcher: sort predictions by confidence, match to the
    highest-IoU unmatched GT above the threshold.

    Returns ``(tp, fp, fn)`` for this item; aggregation across the dataset
    adds them.
    """
    if not predictions and not ground_truth:
        return DetectionItemMetrics(tp=0, fp=0, fn=0, latency_ms=latency_ms)

    sorted_preds = sorted(predictions, key=lambda p: p.confidence, reverse=True)
    matched: set[int] = set()
    tp = 0
    fp = 0

    for pred in sorted_preds:
        best_iou = 0.0
        best_idx: int | None = None
        for idx, gt in enumerate(ground_truth):
            if idx in matched:
                continue
            score = iou(pred.bbox, gt)
            if score > best_iou:
                best_iou = score
                best_idx = idx
        if best_idx is not None and best_iou >= iou_threshold:
            matched.add(best_idx)
            tp += 1
        else:
            fp += 1

    fn = len(ground_truth) - len(matched)
    return DetectionItemMetrics(
        tp=tp,
        fp=fp,
        fn=fn,
        latency_ms=latency_ms,
        matched_gt_indices=sorted(matched),
    )


@dataclass(frozen=True, slots=True)
class DetectionAggregate:
    """Aggregated detection metrics over a whole dataset."""

    precision: Decimal
    recall: Decimal
    f1: Decimal
    mean_latency_ms: Decimal
    items_evaluated: int
    items_failed: int
    total_tp: int
    total_fp: int
    total_fn: int

    def as_summary(self) -> dict[str, float]:
        """JSON-friendly dict for ``experiments.summary_metrics``."""
        return {
            "precision": float(self.precision),
            "recall": float(self.recall),
            "f1": float(self.f1),
            "mean_latency_ms": float(self.mean_latency_ms),
            "items_evaluated": float(self.items_evaluated),
            "items_failed": float(self.items_failed),
            "total_tp": float(self.total_tp),
            "total_fp": float(self.total_fp),
            "total_fn": float(self.total_fn),
        }

    def as_metrics(self) -> dict[str, Decimal]:
        """``Decimal``-typed metrics for the ``model_metrics`` upsert."""
        return {
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "mean_latency_ms": self.mean_latency_ms,
        }


def aggregate_detection(
    items: Iterable[DetectionItemMetrics],
    *,
    failed: int = 0,
) -> DetectionAggregate:
    """Sum TP/FP/FN across items, derive P/R/F1, plus mean latency."""
    total_tp = 0
    total_fp = 0
    total_fn = 0
    total_latency = 0
    n = 0
    for item in items:
        total_tp += item.tp
        total_fp += item.fp
        total_fn += item.fn
        total_latency += item.latency_ms
        n += 1

    precision = _safe_div(total_tp, total_tp + total_fp)
    recall = _safe_div(total_tp, total_tp + total_fn)
    if precision + recall == Decimal("0"):
        f1 = Decimal("0")
    else:
        f1 = (Decimal("2") * precision * recall) / (precision + recall)
    mean_latency = _round6(Decimal(total_latency) / Decimal(n)) if n else Decimal("0")
    return DetectionAggregate(
        precision=_round6(precision),
        recall=_round6(recall),
        f1=_round6(f1),
        mean_latency_ms=mean_latency,
        items_evaluated=n,
        items_failed=failed,
        total_tp=total_tp,
        total_fp=total_fp,
        total_fn=total_fn,
    )


def _safe_div(num: int, den: int) -> Decimal:
    if den == 0:
        return Decimal("0")
    return Decimal(num) / Decimal(den)


def _round6(value: Decimal) -> Decimal:
    """Round to 6 decimal places — fits ``model_metrics.metric_value``."""
    return value.quantize(Decimal("0.000001"))


__all__ = [
    "DetectionAggregate",
    "DetectionItemMetrics",
    "GroundTruthBox",
    "aggregate_detection",
    "evaluate_detection_item",
    "iou",
]
