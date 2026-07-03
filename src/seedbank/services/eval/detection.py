"""Detection eval — IoU matching + precision/recall/F1 + mean Average Precision.

Class-agnostic: every box (predicted or ground-truth) is treated as one
"seed" class, so the metrics measure *localization* quality — does the
detector find the seeds — independent of the label taxonomy. This is the
right call for datasets whose class ids don't map onto the detector's
classes (e.g. a Roboflow export vs a coffee/maize detector).

The matcher is greedy: predictions are sorted by descending confidence,
then each prediction is matched against the highest-IoU unmatched ground
truth box that exceeds the threshold. This is the standard PASCAL VOC
matching protocol at a single IoU value, shared by both the single-threshold
P/R/F1 aggregation and the multi-threshold mAP computation.

mAP follows the COCO convention: Average Precision is the area under the
(all-points-interpolated) precision-recall curve, and ``map_50_95`` averages
AP over IoU thresholds ``0.50, 0.55, …, 0.95``. ``map_50`` / ``map_75`` are
AP at the single 0.50 / 0.75 thresholds.

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


@dataclass(frozen=True, slots=True)
class PredictionMatch:
    """One prediction's outcome after greedy matching against ground truth.

    ``gt_index`` is the index of the ground-truth box this prediction claimed
    (``None`` for a false positive). ``is_tp`` is ``gt_index is not None``.
    """

    confidence: float
    is_tp: bool
    gt_index: int | None


def match_predictions(
    predictions: list[Detection],
    ground_truth: list[GroundTruthBox],
    iou_threshold: float,
) -> list[PredictionMatch]:
    """Greedy IoU matcher shared by P/R/F1 and mAP.

    Predictions are sorted by descending confidence; each claims the
    highest-IoU as-yet-unmatched ground-truth box above ``iou_threshold``
    (one prediction per GT). Returns one :class:`PredictionMatch` per
    prediction, in confidence-descending order.
    """
    sorted_preds = sorted(predictions, key=lambda p: p.confidence, reverse=True)
    matched: set[int] = set()
    out: list[PredictionMatch] = []

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
            out.append(PredictionMatch(confidence=pred.confidence, is_tp=True, gt_index=best_idx))
        else:
            out.append(PredictionMatch(confidence=pred.confidence, is_tp=False, gt_index=None))

    return out


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

    matches = match_predictions(predictions, ground_truth, iou_threshold)
    matched = [m.gt_index for m in matches if m.gt_index is not None]
    tp = len(matched)
    fp = len(matches) - tp
    fn = len(ground_truth) - tp
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


# COCO's ten IoU thresholds — 0.50, 0.55, …, 0.95.
COCO_IOU_THRESHOLDS: tuple[float, ...] = tuple(round(0.5 + 0.05 * i, 2) for i in range(10))


def average_precision(scored: list[tuple[float, bool]], total_gt: int) -> Decimal:
    """Average Precision from confidence-scored predictions.

    ``scored`` is ``(confidence, is_true_positive)`` for every prediction
    across the dataset at one IoU threshold; ``total_gt`` is the total number
    of ground-truth boxes. Predictions are ranked by descending confidence,
    the cumulative precision-recall curve is built, precision is interpolated
    to be monotonically non-increasing (COCO / VOC-2010 "all points"), and AP
    is the area under it. Returns ``0`` when there is no ground truth or no
    prediction.
    """
    if total_gt <= 0 or not scored:
        return Decimal("0")

    ordered = sorted(scored, key=lambda s: s[0], reverse=True)
    tp_cum = 0
    fp_cum = 0
    precisions: list[float] = []
    recalls: list[float] = []
    for _confidence, is_tp in ordered:
        if is_tp:
            tp_cum += 1
        else:
            fp_cum += 1
        precisions.append(tp_cum / (tp_cum + fp_cum))
        recalls.append(tp_cum / total_gt)

    # Interpolate precision: at each recall level use the max precision seen
    # at that recall or higher (walk right-to-left).
    for i in range(len(precisions) - 2, -1, -1):
        precisions[i] = max(precisions[i], precisions[i + 1])

    # Integrate precision over the recall deltas. FP steps leave recall flat,
    # so they contribute nothing.
    ap = 0.0
    prev_recall = 0.0
    for precision, recall in zip(precisions, recalls, strict=True):
        ap += precision * (recall - prev_recall)
        prev_recall = recall

    return _round6(Decimal(str(ap)))


def compute_map(
    per_image: list[tuple[list[Detection], list[GroundTruthBox]]],
    iou_thresholds: Iterable[float] = COCO_IOU_THRESHOLDS,
) -> dict[str, Decimal]:
    """Class-agnostic mean Average Precision over a whole dataset.

    ``per_image`` is one ``(predictions, ground_truth)`` pair per evaluated
    image. Matching is done per image (a prediction can only claim a GT box in
    its own image), but the precision-recall curve is built over the *global*
    pool of predictions ranked by confidence — the standard detection-AP
    protocol. Returns ``map_50`` (AP@0.50), ``map_75`` (AP@0.75) and
    ``map_50_95`` (mean AP over the ten COCO thresholds).
    """
    thresholds = list(iou_thresholds)
    total_gt = sum(len(gt) for _preds, gt in per_image)

    ap_by_threshold: dict[float, Decimal] = {}
    for threshold in thresholds:
        scored: list[tuple[float, bool]] = []
        for preds, gt in per_image:
            for match in match_predictions(preds, gt, threshold):
                scored.append((match.confidence, match.is_tp))
        ap_by_threshold[threshold] = average_precision(scored, total_gt)

    if thresholds:
        mean_ap = _round6(sum(ap_by_threshold.values(), Decimal("0")) / Decimal(len(thresholds)))
    else:
        mean_ap = Decimal("0")

    return {
        "map_50": ap_by_threshold.get(0.5, Decimal("0")),
        "map_75": ap_by_threshold.get(0.75, Decimal("0")),
        "map_50_95": mean_ap,
    }


def _safe_div(num: int, den: int) -> Decimal:
    if den == 0:
        return Decimal("0")
    return Decimal(num) / Decimal(den)


def _round6(value: Decimal) -> Decimal:
    """Round to 6 decimal places — fits ``model_metrics.metric_value``."""
    return value.quantize(Decimal("0.000001"))


__all__ = [
    "COCO_IOU_THRESHOLDS",
    "DetectionAggregate",
    "DetectionItemMetrics",
    "GroundTruthBox",
    "PredictionMatch",
    "aggregate_detection",
    "average_precision",
    "compute_map",
    "evaluate_detection_item",
    "iou",
    "match_predictions",
]
