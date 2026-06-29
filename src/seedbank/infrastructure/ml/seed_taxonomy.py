"""Canonical seed taxonomy for the two-stage pipeline.

Single source of truth that replaces the standalone app's ``config.py``:

* ``SUPERCLASSES`` — the 20 Stage-1 (Faster R-CNN) detector classes, in head
  order (detector index 1-20; index 0 is background). Each maps to a catalog
  ``seed_types.code``.
* ``SPECIALISTS`` — the subset of superclasses that have a trained Stage-2
  EfficientNet-B2 specialist, with the builder key, ordered defect class names,
  and decision threshold the classifier config needs.

``scripts/seed_dev.py`` seeds the catalog from ``SUPERCLASSES``; the model
registration script reads both tables to register Stage-1 + Stage-2 artifacts
with matching ``class_map`` / ``classes`` config. Keep this file framework-free
(no torch) so the API process can import it for validation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Superclass:
    index: int  # Stage-1 detector class id (1-20)
    code: str  # seed_types.code
    display_name: str


@dataclass(frozen=True, slots=True)
class Specialist:
    code: str  # seed_types.code this classifier serves
    builder_key: str  # registry builder key
    classes: tuple[str, ...]  # ordered defect/quality class names (logit order)
    threshold: float = 0.5
    image_size: int = 260  # EfficientNet-B2 native input
    segment: bool = True  # run U2NET background removal before classifying


# Stage-1 superclass head (index → code). Mirrors RCNN_CLASS_MAP in the app.
SUPERCLASSES: tuple[Superclass, ...] = (
    Superclass(1, "soybean", "Soybean"),
    Superclass(2, "nigella", "Nigella (Habbat al-Barakah)"),
    Superclass(3, "ajwain", "Ajwain"),
    Superclass(4, "black_channa", "Black Channa"),
    Superclass(5, "black_pepper", "Black Pepper"),
    Superclass(6, "garlic", "Garlic"),
    Superclass(7, "green_matar", "Green Matar"),
    Superclass(8, "kabuli_channa", "Kabuli Channa"),
    Superclass(9, "rice_paddy", "Rice Paddy"),
    Superclass(10, "wheat_grain", "Wheat Grain"),
    Superclass(11, "white_matar", "White Matar"),
    Superclass(12, "black_sesame", "Black Sesame"),
    Superclass(13, "maize", "Maize"),
    Superclass(14, "chia_seeds", "Chia Seeds"),
    Superclass(15, "cucumber", "Cucumber"),
    Superclass(16, "cumin", "Cumin"),
    Superclass(17, "fennel", "Fennel"),
    Superclass(18, "okra", "Okra"),
    Superclass(19, "pumpkin", "Pumpkin"),
    Superclass(20, "white_sesame", "White Sesame"),
)

# Detector class-id → seed-type code, stored on the detection model's config so
# the worker can route each crop to its specialist.
CLASS_MAP: dict[int, str] = {sc.index: sc.code for sc in SUPERCLASSES}

# Stage-2 specialists. ``classes`` order matches the trained checkpoint's logit
# order (see STAGE2_MODELS in seed-bank-app/config.py). Single-superclass seeds
# (pumpkin, okra, cucumber, …) intentionally have no specialist.
SPECIALISTS: tuple[Specialist, ...] = (
    Specialist(
        "maize",
        "efficientnet-b2-cbam-maize-v1",
        (
            "Broken_MAIZE",
            "Damage_MAIZE",
            "Fungus_MAIZE",
            "Healthy_MAIZE",
            "Immature_MAIZE",
            "Shriveled_MAIZE",
            "Weeveled_MAIZE",
        ),
    ),
    Specialist(
        "soybean",
        "efficientnet-b2-cbam-soybean-v1",
        (
            "01_intact_SOYBEAN",
            "02_cercospora_SOYBEAN",
            "03_greenish_SOYBEAN",
            "04_mechanical_SOYBEAN",
            "05_bug_SOYBEAN",
            "06_dirty_SOYBEAN",
            "07_humidity_SOYBEAN",
        ),
    ),
    Specialist("garlic", "efficientnet-b2-cbam-garlic-v1", ("GOOD_GARLIC", "BAD_GARLIC")),
    Specialist(
        "black_channa",
        "efficientnet-b2-cbam-black-channa-v1",
        ("GOOD_BLACK_CHANNA", "BAD_BLACK_CHANNA"),
    ),
    Specialist(
        "black_pepper",
        "efficientnet-b2-cbam-black-pepper-v1",
        ("GOOD_BLACK_PEPPER", "BAD_BLACK_PEPPER"),
    ),
    Specialist(
        "green_matar",
        "efficientnet-b2-cbam-green-matar-v1",
        ("GOOD_GREEN_MATAR", "BAD_GREEN_MATAR"),
    ),
    Specialist(
        "kabuli_channa",
        "efficientnet-b2-cbam-kabuli-channa-v1",
        ("GOOD_KABULI_CHANNA", "BAD_KABULI_CHANA"),
    ),
    Specialist(
        "rice_paddy",
        "efficientnet-b2-cbam-rice-paddy-v1",
        ("GOOD_RICE_PADDY", "BAD_RICE_PADDY"),
    ),
    Specialist(
        "wheat_grain",
        "efficientnet-b2-cbam-wheat-grain-v1",
        ("GOOD_WHEAT_GRAIN", "BAD_WHEAT_GRAIN"),
    ),
    Specialist(
        "white_matar",
        "efficientnet-b2-cbam-white-matar-v1",
        ("GOOD_WHITE_MATAR", "BAD_WHITE_MATAR"),
    ),
)

SPECIALISTS_BY_CODE: dict[str, Specialist] = {s.code: s for s in SPECIALISTS}

DETECTOR_BUILDER_KEY = "faster-rcnn-resnet50-pan-v1"
DETECTOR_NUM_CLASSES = 21  # 20 superclasses + background


__all__ = [
    "CLASS_MAP",
    "DETECTOR_BUILDER_KEY",
    "DETECTOR_NUM_CLASSES",
    "SPECIALISTS",
    "SPECIALISTS_BY_CODE",
    "SUPERCLASSES",
    "Specialist",
    "Superclass",
]
