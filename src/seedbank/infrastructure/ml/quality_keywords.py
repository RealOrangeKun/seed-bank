"""Class-name → good/bad quality, the single source of truth.

The trainer's final rule (mirrored from the standalone app): a class name is
**bad** when it carries any "red" (defect) keyword, and **good** otherwise. There
is no "uncertain" verdict at this layer — a detected seed that isn't flagged as a
defect is graded good (e.g. ``GREENISH``/``IMMATURE``/``HEALTHY`` all → good, and
ungradeable single-type seeds like ``AJWAIN`` → good).

Both quality paths use this: the YOLO one-shot detector
(:mod:`seedbank.infrastructure.ml.yolo_taxonomy`) maps each detected class name,
and the EfficientNet-B2 specialists
(:mod:`seedbank.infrastructure.ml.backends.torch_local`) map their single fired
class. EfficientNet additionally has its *own* "uncertain" notion driven by the
fired-label count (0 or ≥2), kept only as an observability signal — the worker
stores those (and ungraded detections) as ``good`` too, so a NULL
``seed_detections.quality`` no longer means "uncertain": it only remains for a
genuine classify crash. Keeping the keyword list here means a new defect class
name grades correctly everywhere without touching either path.

Framework-free (no torch) so it imports anywhere.
"""

from __future__ import annotations

# Defect markers — the only thing that makes a detection ``bad``.
RED_KEYWORDS: tuple[str, ...] = (
    "BAD",
    "BROKEN",
    "CERCOSPORA",
    "MECHANICAL",
    "BUG",
    "DIRTY",
    "HUMIDITY",
    "WEEVELED",
    "SHRIVELED",
    "DAMAGE",
    "FUNGUS",
)


def quality_from_label(name: str | None) -> str | None:
    """Return ``"bad"`` if the name carries a defect keyword, else ``"good"``.

    Returns ``None`` only for a falsy name (a pathological, nameless detection) —
    callers decide what to do with that. Any real class name grades good/bad.
    """
    if not name:
        return None
    upper = name.upper()
    return "bad" if any(k in upper for k in RED_KEYWORDS) else "good"


__all__ = ["RED_KEYWORDS", "quality_from_label"]
