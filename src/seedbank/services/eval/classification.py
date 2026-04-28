"""Classification eval — accuracy + macro-F1 over the ``good`` / ``bad`` enum.

The seed-bank classifier is binary (:class:`SeedQuality`). The metrics
returned mirror what :mod:`detection` returns for compatibility with the
``model_metrics`` upsert: a flat ``dict[str, Decimal]`` plus a
JSON-friendly summary for ``experiments.summary_metrics``.

Anything outside the binary label set is treated as a miss — predictions
land as a wrong label and the row counts as failed so the worker can
distinguish "misclassified" from "model returned garbage".
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from seedbank.infrastructure.db.enums import SeedQuality

_VALID_LABELS = frozenset(q.value for q in SeedQuality)


@dataclass(slots=True)
class ClassificationItemResult:
    """One classified item: predicted vs ground-truth label + latency."""

    predicted: str
    ground_truth: str
    latency_ms: int


@dataclass(frozen=True, slots=True)
class ClassificationAggregate:
    accuracy: Decimal
    macro_f1: Decimal
    precision_good: Decimal
    recall_good: Decimal
    f1_good: Decimal
    precision_bad: Decimal
    recall_bad: Decimal
    f1_bad: Decimal
    mean_latency_ms: Decimal
    items_evaluated: int
    items_failed: int
    confusion: dict[str, int]

    def as_summary(self) -> dict[str, float | dict[str, int]]:
        return {
            "accuracy": float(self.accuracy),
            "macro_f1": float(self.macro_f1),
            "precision_good": float(self.precision_good),
            "recall_good": float(self.recall_good),
            "f1_good": float(self.f1_good),
            "precision_bad": float(self.precision_bad),
            "recall_bad": float(self.recall_bad),
            "f1_bad": float(self.f1_bad),
            "mean_latency_ms": float(self.mean_latency_ms),
            "items_evaluated": float(self.items_evaluated),
            "items_failed": float(self.items_failed),
            "confusion": dict(self.confusion),
        }

    def as_metrics(self) -> dict[str, Decimal]:
        """Metric rows persisted in ``model_metrics``."""
        return {
            "accuracy": self.accuracy,
            "macro_f1": self.macro_f1,
            "precision_good": self.precision_good,
            "recall_good": self.recall_good,
            "f1_good": self.f1_good,
            "precision_bad": self.precision_bad,
            "recall_bad": self.recall_bad,
            "f1_bad": self.f1_bad,
            "mean_latency_ms": self.mean_latency_ms,
        }


def evaluate_classification_item(
    *,
    predicted: str,
    ground_truth: str,
    latency_ms: int,
) -> ClassificationItemResult:
    """One-shot per-item eval — trivial wrapper for symmetry with the
    detection module. Validation of the labels happens during aggregation.
    """
    return ClassificationItemResult(
        predicted=predicted,
        ground_truth=ground_truth,
        latency_ms=latency_ms,
    )


def aggregate_classification(
    items: Iterable[ClassificationItemResult],
    *,
    failed: int = 0,
) -> ClassificationAggregate:
    """Compute accuracy + per-class precision/recall/F1 + macro-F1.

    Items with a ground-truth label outside the ``good``/``bad`` enum are
    skipped (the dataset is malformed); items with an out-of-range
    prediction are counted as wrong against their GT label.
    """
    confusion: dict[str, int] = {
        "good_pred_good": 0,
        "good_pred_bad": 0,
        "bad_pred_good": 0,
        "bad_pred_bad": 0,
    }
    total_latency = 0
    n = 0
    for it in items:
        if it.ground_truth not in _VALID_LABELS:
            continue
        # Anything not in valid labels gets treated as the opposite label so
        # the row still rolls into the confusion matrix.
        pred = (
            it.predicted
            if it.predicted in _VALID_LABELS
            else (
                SeedQuality.BAD.value
                if it.ground_truth == SeedQuality.GOOD.value
                else SeedQuality.GOOD.value
            )
        )
        key = f"{it.ground_truth}_pred_{pred}"
        confusion[key] = confusion.get(key, 0) + 1
        total_latency += it.latency_ms
        n += 1

    if n == 0:
        zero = Decimal("0")
        return ClassificationAggregate(
            accuracy=zero,
            macro_f1=zero,
            precision_good=zero,
            recall_good=zero,
            f1_good=zero,
            precision_bad=zero,
            recall_bad=zero,
            f1_bad=zero,
            mean_latency_ms=zero,
            items_evaluated=0,
            items_failed=failed,
            confusion=confusion,
        )

    tp_good = confusion["good_pred_good"]
    fn_good = confusion["good_pred_bad"]
    fp_good = confusion["bad_pred_good"]
    tp_bad = confusion["bad_pred_bad"]
    fn_bad = confusion["bad_pred_good"]
    fp_bad = confusion["good_pred_bad"]

    p_good = _safe_div(tp_good, tp_good + fp_good)
    r_good = _safe_div(tp_good, tp_good + fn_good)
    f1_good = _f1(p_good, r_good)

    p_bad = _safe_div(tp_bad, tp_bad + fp_bad)
    r_bad = _safe_div(tp_bad, tp_bad + fn_bad)
    f1_bad = _f1(p_bad, r_bad)

    accuracy = _safe_div(tp_good + tp_bad, n)
    macro_f1 = (f1_good + f1_bad) / Decimal("2")
    mean_latency = Decimal(total_latency) / Decimal(n)

    return ClassificationAggregate(
        accuracy=_round6(accuracy),
        macro_f1=_round6(macro_f1),
        precision_good=_round6(p_good),
        recall_good=_round6(r_good),
        f1_good=_round6(f1_good),
        precision_bad=_round6(p_bad),
        recall_bad=_round6(r_bad),
        f1_bad=_round6(f1_bad),
        mean_latency_ms=_round6(mean_latency),
        items_evaluated=n,
        items_failed=failed,
        confusion=confusion,
    )


def _safe_div(num: int, den: int) -> Decimal:
    if den == 0:
        return Decimal("0")
    return Decimal(num) / Decimal(den)


def _f1(precision: Decimal, recall: Decimal) -> Decimal:
    if precision + recall == Decimal("0"):
        return Decimal("0")
    return (Decimal("2") * precision * recall) / (precision + recall)


def _round6(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.000001"))


__all__ = [
    "ClassificationAggregate",
    "ClassificationItemResult",
    "aggregate_classification",
    "evaluate_classification_item",
]
