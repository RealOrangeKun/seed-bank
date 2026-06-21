"""Unit tests for the detection eval helpers."""

from __future__ import annotations

from decimal import Decimal

import pytest

from seedbank.infrastructure.ml.backends.base import BoundingBox, Detection
from seedbank.services.eval.detection import (
    GroundTruthBox,
    aggregate_detection,
    evaluate_detection_item,
    iou,
)

pytestmark = pytest.mark.unit


def _det(x: float, y: float, w: float, h: float, conf: float = 0.9) -> Detection:
    return Detection(
        bbox=BoundingBox(x=x, y=y, w=w, h=h),
        class_id=0,
        class_name="good",
        confidence=conf,
    )


def _gt(x: float, y: float, w: float, h: float, label: str = "good") -> GroundTruthBox:
    return GroundTruthBox(x=x, y=y, w=w, h=h, label=label)


# ── iou ───────────────────────────────────────────────────────────────────


def test_iou_identical_boxes_is_one() -> None:
    pred = BoundingBox(x=0.1, y=0.1, w=0.2, h=0.2)
    gt = _gt(0.1, 0.1, 0.2, 0.2)
    assert iou(pred, gt) == pytest.approx(1.0)


def test_iou_disjoint_boxes_is_zero() -> None:
    pred = BoundingBox(x=0.0, y=0.0, w=0.1, h=0.1)
    gt = _gt(0.5, 0.5, 0.1, 0.1)
    assert iou(pred, gt) == 0.0


def test_iou_half_overlap() -> None:
    # pred: (0,0,0.2,0.1); gt: (0.1,0,0.2,0.1) → intersection=0.01, union=0.03
    pred = BoundingBox(x=0.0, y=0.0, w=0.2, h=0.1)
    gt = _gt(0.1, 0.0, 0.2, 0.1)
    assert iou(pred, gt) == pytest.approx(1 / 3)


def test_iou_zero_when_box_has_zero_area() -> None:
    pred = BoundingBox(x=0.0, y=0.0, w=0.0, h=0.5)
    gt = _gt(0.0, 0.0, 0.5, 0.5)
    assert iou(pred, gt) == 0.0


# ── evaluate_detection_item ────────────────────────────────────────────────


def test_perfect_predictions_count_only_tp() -> None:
    preds = [_det(0.1, 0.1, 0.2, 0.2), _det(0.5, 0.5, 0.2, 0.2)]
    gts = [_gt(0.1, 0.1, 0.2, 0.2), _gt(0.5, 0.5, 0.2, 0.2)]
    out = evaluate_detection_item(predictions=preds, ground_truth=gts, latency_ms=10)
    assert out.tp == 2
    assert out.fp == 0
    assert out.fn == 0


def test_extra_prediction_counts_as_fp() -> None:
    preds = [
        _det(0.1, 0.1, 0.2, 0.2),
        _det(0.6, 0.6, 0.2, 0.2),  # ghost
    ]
    gts = [_gt(0.1, 0.1, 0.2, 0.2)]
    out = evaluate_detection_item(predictions=preds, ground_truth=gts, latency_ms=10)
    assert out.tp == 1
    assert out.fp == 1
    assert out.fn == 0


def test_missed_ground_truth_counts_as_fn() -> None:
    preds = [_det(0.1, 0.1, 0.2, 0.2)]
    gts = [
        _gt(0.1, 0.1, 0.2, 0.2),
        _gt(0.6, 0.6, 0.2, 0.2),
    ]
    out = evaluate_detection_item(predictions=preds, ground_truth=gts, latency_ms=10)
    assert out.tp == 1
    assert out.fp == 0
    assert out.fn == 1


def test_no_predictions_no_gt_is_clean() -> None:
    out = evaluate_detection_item(predictions=[], ground_truth=[], latency_ms=5)
    assert (out.tp, out.fp, out.fn) == (0, 0, 0)


def test_higher_confidence_wins_match() -> None:
    """Greedy matcher must process predictions by descending confidence."""
    pred_lo = _det(0.1, 0.1, 0.2, 0.2, conf=0.3)
    pred_hi = _det(0.1, 0.1, 0.2, 0.2, conf=0.99)
    gts = [_gt(0.1, 0.1, 0.2, 0.2)]
    out = evaluate_detection_item(predictions=[pred_lo, pred_hi], ground_truth=gts, latency_ms=10)
    # Only one TP can exist; the other prediction is FP.
    assert out.tp == 1
    assert out.fp == 1


# ── aggregate_detection ───────────────────────────────────────────────────


def test_aggregate_computes_p_r_f1_and_mean_latency() -> None:
    items = [
        evaluate_detection_item(
            predictions=[_det(0.1, 0.1, 0.2, 0.2)],
            ground_truth=[_gt(0.1, 0.1, 0.2, 0.2)],
            latency_ms=10,
        ),
        evaluate_detection_item(
            predictions=[_det(0.0, 0.0, 0.05, 0.05)],
            ground_truth=[_gt(0.5, 0.5, 0.2, 0.2)],
            latency_ms=20,
        ),
    ]
    agg = aggregate_detection(items, failed=1)
    # tp=1, fp=1, fn=1 → precision=0.5, recall=0.5, f1=0.5
    assert agg.precision == Decimal("0.500000")
    assert agg.recall == Decimal("0.500000")
    assert agg.f1 == Decimal("0.500000")
    assert agg.mean_latency_ms == Decimal("15.000000")
    assert agg.items_evaluated == 2
    assert agg.items_failed == 1


def test_aggregate_handles_empty_input() -> None:
    agg = aggregate_detection([], failed=0)
    assert agg.precision == Decimal("0")
    assert agg.recall == Decimal("0")
    assert agg.f1 == Decimal("0")
    assert agg.items_evaluated == 0
