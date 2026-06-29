"""EfficientNet-B2 + CBAM Stage-2 specialist classifiers.

One builder per seed superclass that has a trained specialist checkpoint in the
standalone app (``checkpoints_<seed>/best_*.pt``). Each specialist is the same
architecture (:class:`SeedQualityClassifier`) differing only in head width —
the number of defect classes for that seed — so we register them with a small
loop rather than ten near-identical files.

Builder keys: ``efficientnet-b2-cbam-<seed>-v1``. The matching defect class
names + per-model threshold live in the ``model_artifacts.config`` row
(``classes`` / ``threshold``), not here — the architecture only needs the count.

Single-superclass seeds (PUMPKIN, OKRA, …) have no specialist: Stage-1 emits the
superclass label directly and classification is skipped for them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from seedbank.infrastructure.ml.builders._efficientnet_b2_cbam import (
    SeedQualityClassifier,
)
from seedbank.infrastructure.ml.registry import register_builder

if TYPE_CHECKING:  # pragma: no cover — torch is in the [inference] extra
    from collections.abc import Callable

    from torch import nn

# seed superclass code → number of defect/quality classes (head width).
# Mirrors STAGE2_MODELS in seed-bank-app/config.py.
_SPECIALIST_CLASS_COUNTS: dict[str, int] = {
    "maize": 7,
    "soybean": 7,
    "garlic": 2,
    "black_channa": 2,
    "black_pepper": 2,
    "green_matar": 2,
    "kabuli_channa": 2,
    "rice_paddy": 2,
    "wheat_grain": 2,
    "white_matar": 2,
}


def _make_builder(num_classes: int) -> Callable[[], nn.Module]:
    def build() -> nn.Module:
        return SeedQualityClassifier(num_classes=num_classes, pretrained=False, dropout=0.0)

    return build


# Register one builder per specialist at import time (autodiscovery triggers it).
for _seed, _count in _SPECIALIST_CLASS_COUNTS.items():
    register_builder(f"efficientnet-b2-cbam-{_seed.replace('_', '-')}-v1")(
        _make_builder(_count)
    )


__all__ = ["_SPECIALIST_CLASS_COUNTS"]
