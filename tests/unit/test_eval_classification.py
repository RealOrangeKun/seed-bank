"""Unit tests for the classification eval helpers."""

from __future__ import annotations

from decimal import Decimal

import pytest

from seedbank.services.eval.classification import (
    ClassificationItemResult,
    aggregate_classification,
    evaluate_classification_item,
)

pytestmark = pytest.mark.unit


def _it(predicted: str, ground_truth: str, latency: int = 5) -> ClassificationItemResult:
    return evaluate_classification_item(
        predicted=predicted, ground_truth=ground_truth, latency_ms=latency
    )


def test_perfect_classifier_has_accuracy_one_and_macro_f1_one() -> None:
    items = [
        _it("good", "good"),
        _it("good", "good"),
        _it("bad", "bad"),
        _it("bad", "bad"),
    ]
    agg = aggregate_classification(items)
    assert agg.accuracy == Decimal("1.000000")
    assert agg.f1_good == Decimal("1.000000")
    assert agg.f1_bad == Decimal("1.000000")
    assert agg.macro_f1 == Decimal("1.000000")


def test_all_wrong_classifier_has_accuracy_zero() -> None:
    items = [
        _it("good", "bad"),
        _it("bad", "good"),
    ]
    agg = aggregate_classification(items)
    assert agg.accuracy == Decimal("0")


def test_confusion_matrix_counts() -> None:
    items = [
        _it("good", "good"),
        _it("good", "good"),
        _it("bad", "good"),  # missed seed
        _it("bad", "bad"),
        _it("good", "bad"),  # false alarm
    ]
    agg = aggregate_classification(items)
    cm = agg.confusion
    assert cm["good_pred_good"] == 2
    assert cm["good_pred_bad"] == 1
    assert cm["bad_pred_good"] == 1
    assert cm["bad_pred_bad"] == 1
    assert agg.items_evaluated == 5
    # accuracy = (2+1)/5 = 0.6
    assert agg.accuracy == Decimal("0.600000")


def test_invalid_predicted_label_treated_as_opposite() -> None:
    items = [
        _it("ok", "good"),  # invalid pred + GT good → counted as bad
        _it("good", "good"),
    ]
    agg = aggregate_classification(items)
    # 1 correct (good→good), 1 incorrect (good→bad)
    assert agg.accuracy == Decimal("0.500000")


def test_invalid_ground_truth_label_skipped() -> None:
    items = [
        _it("good", "ambiguous"),  # invalid GT — skipped
        _it("good", "good"),
        _it("bad", "bad"),
    ]
    agg = aggregate_classification(items)
    assert agg.items_evaluated == 2
    assert agg.accuracy == Decimal("1.000000")


def test_aggregate_handles_empty_input() -> None:
    agg = aggregate_classification([])
    assert agg.accuracy == Decimal("0")
    assert agg.macro_f1 == Decimal("0")
    assert agg.items_evaluated == 0


def test_mean_latency_arithmetic() -> None:
    items = [
        _it("good", "good", latency=10),
        _it("bad", "bad", latency=20),
        _it("good", "good", latency=30),
    ]
    agg = aggregate_classification(items)
    assert agg.mean_latency_ms == Decimal("20.000000")
