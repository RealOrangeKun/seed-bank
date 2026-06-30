"""Unit tests for the new two-stage model wiring.

Covers the framework-light contracts that don't need a GPU or the weights:
the seed taxonomy's internal consistency, the registry exposing every new
builder key, and the multi-label → good/bad collapse used by the EfficientNet-B2
specialists. The architecture/weight-load checks live in the inference-only
verification script (run on a GPU box), not here.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from seedbank.infrastructure.ml.backends.base import ClassificationConfig
from seedbank.infrastructure.ml.backends.torch_local import _multilabel_classification
from seedbank.infrastructure.ml.quality_keywords import quality_from_label
from seedbank.infrastructure.ml.registry import list_builders
from seedbank.infrastructure.ml.seed_taxonomy import (
    CLASS_MAP,
    SPECIALISTS,
    SPECIALISTS_BY_CODE,
    SUPERCLASSES,
)
from seedbank.infrastructure.ml.yolo_taxonomy import classify_name

# torch is in the [inference] extra; these tests build logits tensors directly.
torch = pytest.importorskip("torch")


def _cfg(classes: tuple[str, ...], threshold: float = 0.5) -> ClassificationConfig:
    return ClassificationConfig(
        model_id=uuid4(),
        artifact_uri="s3://m/k",
        builder_key="efficientnet-b2-cbam-maize-v1",
        threshold=threshold,
        image_size=260,
        classes=classes,
        segment=True,
    )


# ── taxonomy ──────────────────────────────────────────────────────────────────


def test_taxonomy_shapes() -> None:
    assert len(SUPERCLASSES) == 20
    assert len(SPECIALISTS) == 10
    # CLASS_MAP keys are the detector indices 1..20.
    assert sorted(CLASS_MAP) == list(range(1, 21))


def test_every_specialist_code_is_a_superclass() -> None:
    codes = {sc.code for sc in SUPERCLASSES}
    for spec in SPECIALISTS:
        assert spec.code in codes
        assert SPECIALISTS_BY_CODE[spec.code] is spec
        # head width matches the class list length
        assert len(spec.classes) >= 2


# ── registry ──────────────────────────────────────────────────────────────────


def test_registry_exposes_new_builders() -> None:
    keys = set(list_builders())
    assert "faster-rcnn-resnet50-pan-v1" in keys
    for spec in SPECIALISTS:
        assert spec.builder_key in keys
    # Old builders were removed in the model replacement.
    assert "faster-rcnn-combined-v1" not in keys
    assert "resnet18-cbam-coffee-v3" not in keys
    assert "resnet18-cbam-maize-v4" not in keys


# ── multi-label collapse ──────────────────────────────────────────────────────


# ── quality keyword rule (single source of truth) ──────────────────────────────


def test_quality_from_label_keywords() -> None:
    # Canonical rule: a defect (red) keyword → bad, everything else → good.
    assert quality_from_label("Healthy_MAIZE") == "good"
    assert quality_from_label("01_intact_SOYBEAN") == "good"
    assert quality_from_label("GOOD_GARLIC") == "good"
    assert quality_from_label("BAD_GARLIC") == "bad"
    assert quality_from_label("Fungus_MAIZE") == "bad"
    assert quality_from_label("02_cercospora_SOYBEAN") == "bad"
    # GREENISH / IMMATURE carry no defect keyword → good.
    assert quality_from_label("03_greenish_SOYBEAN") == "good"
    assert quality_from_label("Immature_MAIZE") == "good"
    # An ungradeable single-type seed has no defect keyword → good.
    assert quality_from_label("AJWAIN") == "good"
    # Only a falsy name is None (pathological, nameless detection).
    assert quality_from_label("") is None
    assert quality_from_label(None) is None


def test_yolo_classify_name_grades_by_defect_keyword() -> None:
    assert classify_name("03_greenish_SOYBEAN") == ("soybean", "good")
    assert classify_name("Immature_MAIZE") == ("maize", "good")
    assert classify_name("Fungus_MAIZE") == ("maize", "bad")
    assert classify_name("GOOD_GARLIC") == ("garlic", "good")
    # Single-type seed: type resolved, no defect keyword → good.
    assert classify_name("AJWAIN") == ("ajwain", "good")


# ── EfficientNet collapse (exactly-one → keyword; else uncertain) ───────────────
#
# The backend still *emits* "uncertain" for the 0-fired / ≥2-fired cases (kept as
# an observability signal). The worker maps that "uncertain" — and any detection
# of a type with no classifier — to a stored ``good``, so it counts toward the
# good-rate. That worker mapping is exercised at the worker/e2e layer, not here.


def test_multilabel_single_defect_fires_bad() -> None:
    classes = ("Healthy_MAIZE", "Fungus_MAIZE")
    # logits chosen so sigmoid(Healthy) low, sigmoid(Fungus) high → one fires.
    logits = torch.tensor([[-4.0, 4.0]])
    out = _multilabel_classification(logits, _cfg(classes))
    assert out.label == "bad"
    assert "Fungus_MAIZE" in out.defects
    assert 0.0 <= out.confidence <= 1.0


def test_multilabel_single_healthy_fires_good() -> None:
    classes = ("GOOD_GARLIC", "BAD_GARLIC")
    logits = torch.tensor([[5.0, -5.0]])
    out = _multilabel_classification(logits, _cfg(classes))
    assert out.label == "good"
    assert out.defects == ()
    assert out.confidence > 0.9


def test_multilabel_nothing_fires_is_uncertain() -> None:
    classes = ("GOOD_GARLIC", "BAD_GARLIC")
    logits = torch.tensor([[-1.0, -1.0]])  # both below 0.5 → no label
    out = _multilabel_classification(logits, _cfg(classes))
    assert out.label == "uncertain"
    assert out.defects == ()


def test_multilabel_two_fire_is_uncertain() -> None:
    classes = ("Healthy_MAIZE", "Fungus_MAIZE")
    logits = torch.tensor([[4.0, 4.0]])  # both above 0.5 → multi-label
    out = _multilabel_classification(logits, _cfg(classes))
    assert out.label == "uncertain"
    # Both fired names are kept as context.
    assert set(out.defects) == {"Healthy_MAIZE", "Fungus_MAIZE"}
