"""YOLO one-shot class → (seed type, quality) mapping.

The Faster R-CNN path detects a *superclass* and a separate EfficientNet-B2
specialist grades quality. The YOLO "fast mode" detector instead emits a single
fine-grained class per box that already encodes both the seed type *and* its
quality (e.g. ``GOOD_GARLIC``, ``Fungus_MAIZE``, ``01_intact_SOYBEAN``). This
module maps each YOLO class name to a catalog ``seed_types.code``; the good/bad
label comes from the shared keyword rule in
:mod:`seedbank.infrastructure.ml.quality_keywords` (the single source of truth:
a defect keyword → ``bad``, anything else → ``good``, so ungradeable single-type
seeds grade good and a new defect name grades correctly without editing this
table).

Framework-free (no torch) so it can be imported anywhere. ``seed_types.code``
values match :mod:`seedbank.infrastructure.ml.seed_taxonomy`.
"""

from __future__ import annotations

from seedbank.infrastructure.ml.quality_keywords import quality_from_label

# YOLO class name → catalog ``seed_types.code`` for the 40 classes the
# YOLOv11M/v8 seed detector was trained on (mirrors YOLO_CLASSES in
# seed-bank-app/config.py). Quality is derived from the class name via
# ``quality_from_label`` — not stored here — so the two never drift.
_CODE_OF: dict[str, str] = {
    # SOYBEAN
    "01_intact_SOYBEAN": "soybean",
    "02_cercospora_SOYBEAN": "soybean",
    "03_greenish_SOYBEAN": "soybean",
    "04_mechanical_SOYBEAN": "soybean",
    "05_bug_SOYBEAN": "soybean",
    "06_dirty_SOYBEAN": "soybean",
    "07_humidity_SOYBEAN": "soybean",
    # MAIZE
    "Healthy_MAIZE": "maize",
    "Broken_MAIZE": "maize",
    "Damage_MAIZE": "maize",
    "Fungus_MAIZE": "maize",
    "Immature_MAIZE": "maize",
    "Shriveled_MAIZE": "maize",
    "Weeveled_MAIZE": "maize",
    # Binary GOOD_/BAD_ seeds.
    "GOOD_BLACK_CHANNA": "black_channa",
    "BAD_BLACK_CHANNA": "black_channa",
    "GOOD_BLACK_PEPPER": "black_pepper",
    "BAD_BLACK_PEPPER": "black_pepper",
    "GOOD_GARLIC": "garlic",
    "BAD_GARLIC": "garlic",
    "GOOD_GREEN_MATAR": "green_matar",
    "BAD_GREEN_MATAR": "green_matar",
    "GOOD_KABULI_CHANNA": "kabuli_channa",
    "BAD_KABULI_CHANA": "kabuli_channa",  # trained-name typo kept on purpose
    "GOOD_RICE_PADDY": "rice_paddy",
    "BAD_RICE_PADDY": "rice_paddy",
    "GOOD_WHEAT_GRAIN": "wheat_grain",
    "BAD_WHEAT_GRAIN": "wheat_grain",
    "GOOD_WHITE_MATAR": "white_matar",
    "BAD_WHITE_MATAR": "white_matar",
    # Single-type seeds the model doesn't grade — type only, no quality keyword.
    "7ABET_2LBARAKA": "nigella",
    "AJWAIN": "ajwain",
    "Black_sesame": "black_sesame",
    "CHIA_SEEDS": "chia_seeds",
    "CUCUMBER": "cucumber",
    "CUMIN": "cumin",
    "Fennel": "fennel",
    "OKRA": "okra",
    "PUMPKIN": "pumpkin",
    "WHITE_SESAME": "white_sesame",
}

# Case-insensitive index for resilience to minor casing differences in the
# model's exported ``names``.
_CODE_OF_CI: dict[str, str] = {k.upper(): v for k, v in _CODE_OF.items()}

# Seed-type code → compact uppercase form, for the heuristic fallback below.
_CODES = (
    "soybean",
    "nigella",
    "ajwain",
    "black_channa",
    "black_pepper",
    "garlic",
    "green_matar",
    "kabuli_channa",
    "rice_paddy",
    "wheat_grain",
    "white_matar",
    "black_sesame",
    "maize",
    "chia_seeds",
    "cucumber",
    "cumin",
    "fennel",
    "okra",
    "pumpkin",
    "white_sesame",
)


def classify_name(name: str | None) -> tuple[str | None, str | None]:
    """Map a YOLO class name to ``(seed_type_code, quality)``.

    Quality is the shared keyword rule (good/bad/None). The seed type comes from
    the explicit table, falling back to any embedded catalog code for an
    unknown name. Returns ``(None, None)`` when nothing matches.
    """
    if not name:
        return None, None

    quality = quality_from_label(name)

    code = _CODE_OF_CI.get(name.upper())
    if code is not None:
        return code, quality

    compact = name.upper().replace("_", "").replace(" ", "")
    for c in _CODES:
        if c.replace("_", "").upper() in compact:
            return c, quality
    return None, quality


__all__ = ["classify_name"]
