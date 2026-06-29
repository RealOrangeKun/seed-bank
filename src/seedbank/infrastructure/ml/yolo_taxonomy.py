"""YOLO one-shot class → (seed type, quality) mapping.

The Faster R-CNN path detects a *superclass* and a separate EfficientNet-B2
specialist grades quality. The YOLO "fast mode" detector instead emits a single
fine-grained class per box that already encodes both the seed type *and* its
quality (e.g. ``GOOD_GARLIC``, ``Fungus_MAIZE``, ``01_intact_SOYBEAN``). This
module maps each YOLO class name to a catalog ``seed_types.code`` + a good/bad
label so the worker can persist graded detections directly, skipping the
two-stage classify step.

Framework-free (no torch) so it can be imported anywhere. ``seed_types.code``
values match :mod:`seedbank.infrastructure.ml.seed_taxonomy`.
"""

from __future__ import annotations

# Explicit map for the 40 classes the YOLOv11M/v8 seed detector was trained on
# (mirrors YOLO_CLASSES in seed-bank-app/config.py). Value = (seed_type_code,
# quality) where quality is "good" | "bad" | None (single-type seeds the model
# doesn't grade).
_MAP: dict[str, tuple[str, str | None]] = {
    # SOYBEAN — 01_intact is good, the rest are defects.
    "01_intact_SOYBEAN": ("soybean", "good"),
    "02_cercospora_SOYBEAN": ("soybean", "bad"),
    "03_greenish_SOYBEAN": ("soybean", "bad"),
    "04_mechanical_SOYBEAN": ("soybean", "bad"),
    "05_bug_SOYBEAN": ("soybean", "bad"),
    "06_dirty_SOYBEAN": ("soybean", "bad"),
    "07_humidity_SOYBEAN": ("soybean", "bad"),
    # MAIZE — Healthy is good, the rest are defects.
    "Healthy_MAIZE": ("maize", "good"),
    "Broken_MAIZE": ("maize", "bad"),
    "Damage_MAIZE": ("maize", "bad"),
    "Fungus_MAIZE": ("maize", "bad"),
    "Immature_MAIZE": ("maize", "bad"),
    "Shriveled_MAIZE": ("maize", "bad"),
    "Weeveled_MAIZE": ("maize", "bad"),
    # Binary GOOD_/BAD_ seeds.
    "GOOD_BLACK_CHANNA": ("black_channa", "good"),
    "BAD_BLACK_CHANNA": ("black_channa", "bad"),
    "GOOD_BLACK_PEPPER": ("black_pepper", "good"),
    "BAD_BLACK_PEPPER": ("black_pepper", "bad"),
    "GOOD_GARLIC": ("garlic", "good"),
    "BAD_GARLIC": ("garlic", "bad"),
    "GOOD_GREEN_MATAR": ("green_matar", "good"),
    "BAD_GREEN_MATAR": ("green_matar", "bad"),
    "GOOD_KABULI_CHANNA": ("kabuli_channa", "good"),
    "BAD_KABULI_CHANA": ("kabuli_channa", "bad"),  # trained-name typo kept on purpose
    "GOOD_RICE_PADDY": ("rice_paddy", "good"),
    "BAD_RICE_PADDY": ("rice_paddy", "bad"),
    "GOOD_WHEAT_GRAIN": ("wheat_grain", "good"),
    "BAD_WHEAT_GRAIN": ("wheat_grain", "bad"),
    "GOOD_WHITE_MATAR": ("white_matar", "good"),
    "BAD_WHITE_MATAR": ("white_matar", "bad"),
    # Single-type seeds the model doesn't grade — type only, no quality.
    "7ABET_2LBARAKA": ("nigella", None),
    "AJWAIN": ("ajwain", None),
    "Black_sesame": ("black_sesame", None),
    "CHIA_SEEDS": ("chia_seeds", None),
    "CUCUMBER": ("cucumber", None),
    "CUMIN": ("cumin", None),
    "Fennel": ("fennel", None),
    "OKRA": ("okra", None),
    "PUMPKIN": ("pumpkin", None),
    "WHITE_SESAME": ("white_sesame", None),
}

# Case-insensitive index for resilience to minor casing differences in the
# model's exported ``names``.
_MAP_CI: dict[str, tuple[str, str | None]] = {k.upper(): v for k, v in _MAP.items()}

# Seed-type code → compact uppercase form, for the heuristic fallback below.
_CODES = (
    "soybean", "nigella", "ajwain", "black_channa", "black_pepper", "garlic",
    "green_matar", "kabuli_channa", "rice_paddy", "wheat_grain", "white_matar",
    "black_sesame", "maize", "chia_seeds", "cucumber", "cumin", "fennel",
    "okra", "pumpkin", "white_sesame",
)
_HEALTHY = ("GOOD", "HEALTHY", "INTACT")


def classify_name(name: str | None) -> tuple[str | None, str | None]:
    """Map a YOLO class name to ``(seed_type_code, quality)``.

    Unknown names fall back to a heuristic: derive quality from
    good/healthy/intact vs bad/defect markers, and the seed type from any
    embedded catalog code. Returns ``(None, None)`` when nothing matches.
    """
    if not name:
        return None, None
    hit = _MAP_CI.get(name.upper())
    if hit is not None:
        return hit

    upper = name.upper()
    quality: str | None = None
    if "BAD" in upper:
        quality = "bad"
    elif any(m in upper for m in _HEALTHY):
        quality = "good"

    compact = upper.replace("_", "").replace(" ", "")
    code: str | None = None
    for c in _CODES:
        if c.replace("_", "").upper() in compact:
            code = c
            break
    return code, quality


__all__ = ["classify_name"]
