"""Unit tests for the experiment Markdown report renderer."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from seedbank.services.eval.report import render_report

pytestmark = pytest.mark.unit


def test_report_includes_header_and_metric_rows() -> None:
    text = render_report(
        experiment_id=uuid4(),
        experiment_name="exp-x",
        model_id=uuid4(),
        model_name="resnet18",
        model_version="v1",
        dataset_id=uuid4(),
        dataset_name="ds-x",
        kind="detection",
        summary={"precision": 0.9, "recall": 0.8, "f1": 0.85, "mean_latency_ms": 12.5},
        started_at=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        finished_at=datetime(2026, 5, 1, 12, 0, 5, tzinfo=UTC),
        duration_ms=5000,
        items_evaluated=42,
        items_failed=1,
    )
    assert text.startswith("# Experiment exp-x")
    assert "## Summary metrics" in text
    assert "`precision`" in text
    assert "0.900000" in text
    assert "Items evaluated" in text


def test_report_renders_confusion_matrix_for_classification() -> None:
    text = render_report(
        experiment_id=uuid4(),
        experiment_name="exp-cls",
        model_id=uuid4(),
        model_name="cnn",
        model_version="v3",
        dataset_id=uuid4(),
        dataset_name="ds-cls",
        kind="classification",
        summary={
            "accuracy": 0.9,
            "macro_f1": 0.88,
            "confusion": {
                "good_pred_good": 5,
                "good_pred_bad": 1,
                "bad_pred_good": 0,
                "bad_pred_bad": 4,
            },
        },
        started_at=None,
        finished_at=None,
        duration_ms=None,
        items_evaluated=10,
        items_failed=0,
    )
    assert "## Confusion matrix" in text
    assert "| **good** |" in text
    assert "| **bad** |" in text


def test_report_handles_missing_optional_fields() -> None:
    text = render_report(
        experiment_id=uuid4(),
        experiment_name="exp",
        model_id=uuid4(),
        model_name="m",
        model_version="v1",
        dataset_id=uuid4(),
        dataset_name="d",
        kind="detection",
        summary={"precision": 1.0},
        started_at=None,
        finished_at=None,
        duration_ms=None,
        items_evaluated=1,
        items_failed=0,
    )
    assert "n/a" in text  # missing started_at / finished_at
