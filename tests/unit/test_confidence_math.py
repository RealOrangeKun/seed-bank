"""Unit tests for the confidence/quality math in app.ml.detection_pipeline.

These exercise calculate_confidence_from_logits, which is the live confidence logic
(BCEWithLogits based), independent of any model weights.
"""
import pytest

from app.ml.detection_pipeline import calculate_confidence_from_logits


@pytest.mark.parametrize("logits,threshold", [
    (10.0, 5.0),   # clearly good (maize)
    (0.0, 5.0),    # clearly bad (maize)
    (5.0, 5.0),    # exactly on the maize threshold
    (1.0, 0.0),    # clearly good (coffee)
    (-3.0, 0.0),   # clearly bad (coffee)
    (0.0, 0.0),    # exactly on the coffee threshold
])
def test_percentages_are_complementary_and_bounded(logits, threshold):
    r = calculate_confidence_from_logits(logits, threshold)
    # good + bad must always sum to 100 (they are complementary)
    assert r["good_percentage"] + r["bad_percentage"] == pytest.approx(100.0, abs=0.011)
    for key in ("good_percentage", "bad_percentage", "classification_confidence"):
        assert 0.0 <= r[key] <= 100.0, f"{key} out of range: {r[key]}"


def test_good_when_at_or_above_threshold():
    # logits == threshold is classified Good (>=) by the pipeline.
    r = calculate_confidence_from_logits(5.0, 5.0)
    assert r["good_percentage"] >= r["bad_percentage"]


def test_bad_when_below_threshold():
    r = calculate_confidence_from_logits(-1.0, 0.0)
    assert r["bad_percentage"] >= r["good_percentage"]


def test_confident_good_beats_borderline_good():
    """A logit far above threshold should read as more 'good' than one barely above."""
    far = calculate_confidence_from_logits(50.0, 5.0)
    near = calculate_confidence_from_logits(5.1, 5.0)
    assert far["good_percentage"] >= near["good_percentage"]


def test_raw_logits_passthrough():
    r = calculate_confidence_from_logits(7.1234, 5.0)
    assert r["raw_logits"] == pytest.approx(7.1234, abs=1e-3)


def test_classification_confidence_is_sigmoid_based():
    # at logit 0 sigmoid is 0.5 -> 50%
    r = calculate_confidence_from_logits(0.0, 0.0)
    assert r["classification_confidence"] == pytest.approx(50.0, abs=0.5)
