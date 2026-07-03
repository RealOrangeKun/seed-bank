"""YOLO dataset import — pure parsing + archive-unpacking helpers.

No IO, no SQLAlchemy, no Celery. The Celery task in
:mod:`seedbank.workers.tasks.dataset_import` orchestrates MinIO/DB and calls
these to turn an uploaded ``.zip`` (``images/`` + ``labels/``, YOLO
annotations) into dataset items.

YOLO labels are one box per line ``class_id xc yc w h``, all normalized to
``[0, 1]`` and **center-based**. The platform stores boxes **top-left-corner**
based (see :func:`seedbank.services.eval.detection.iou` and the model
backends), so ingest converts ``x = xc - w/2``, ``y = yc - h/2`` here — the
single place the two conventions meet. Labels are class-agnostic downstream
(the detection evaluator matches by IoU, ignoring the class), so the raw
``class_id`` is preserved only as the box ``label`` for traceability.
"""

from __future__ import annotations

import io
import posixpath
import zipfile
from dataclasses import dataclass
from typing import Any

from seedbank.core.exceptions import ValidationError


@dataclass(frozen=True, slots=True)
class YoloArchiveEntry:
    """One archived image (referenced by its zip member path) plus its parsed
    ground-truth boxes.

    Holds **no image bytes** — the caller reads each image lazily from the open
    archive one at a time, so a large dataset never sits in memory all at once.
    """

    member_name: str
    filename: str
    boxes: list[dict[str, Any]]


def parse_yolo_label(text: str) -> list[dict[str, Any]]:
    """Parse YOLO label text into canonical corner-format boxes.

    Handles both YOLO annotation shapes, one per non-blank line:

    * **Detection** — ``class_id xc yc w h`` (5 fields, center-based) → the
      top-left-corner box.
    * **Segmentation** — ``class_id x1 y1 x2 y2 ...`` (an odd field count ≥ 7, a
      normalized polygon) → its axis-aligned **bounding box**. The detection
      evaluator matches on box IoU, so a polygon collapses to the box that
      encloses it.

    All coordinates are normalized ``[0, 1]``. Returns
    ``[{"x", "y", "w", "h", "label"}, ...]`` with ``x, y`` the top-left corner
    and ``label`` the raw ``class_id`` (class-agnostic downstream).
    Blank/whitespace-only input → ``[]`` (a valid background image). Raises
    :class:`ValidationError` on a malformed line or an out-of-range value.
    """
    boxes: list[dict[str, Any]] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        n = len(parts)
        if n != 5 and not (n >= 7 and n % 2 == 1):
            raise ValidationError(
                f"YOLO label line {lineno} must have 5 fields (detection: "
                f"class_id xc yc w h) or an odd count ≥ 7 (segmentation polygon), "
                f"got {n}."
            )
        try:
            class_id = int(float(parts[0]))
            coords = [float(p) for p in parts[1:]]
        except ValueError as exc:
            raise ValidationError(f"YOLO label line {lineno}: non-numeric field.") from exc

        for value in coords:
            if not 0.0 <= value <= 1.0:
                raise ValidationError(
                    f"YOLO label line {lineno}: coordinate {value} out of range [0, 1]."
                )

        if n == 5:
            xc, yc, w, h = coords
        else:
            # Polygon → the axis-aligned bounding box of its vertices.
            xs, ys = coords[0::2], coords[1::2]
            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)
            xc, yc = (x_min + x_max) / 2.0, (y_min + y_max) / 2.0
            w, h = x_max - x_min, y_max - y_min

        if w <= 0.0 or h <= 0.0:
            raise ValidationError(f"YOLO label line {lineno}: width/height must be > 0.")

        # center → top-left corner; clamp the tiny negatives that a box flush
        # against an edge can produce so downstream stays within [0, 1].
        x = min(max(xc - w / 2.0, 0.0), 1.0)
        y = min(max(yc - h / 2.0, 0.0), 1.0)
        boxes.append({"x": x, "y": y, "w": w, "h": h, "label": str(class_id)})
    return boxes


def _is_unsafe_path(name: str) -> bool:
    """True for absolute paths or ``..`` traversal (zip-slip guard)."""
    norm = posixpath.normpath(name)
    return norm.startswith("/") or norm == ".." or norm.startswith("../")


def open_yolo_archive(source: str | io.BytesIO) -> zipfile.ZipFile:
    """Open a ``.zip`` from a filesystem path or in-memory buffer, mapping a
    corrupt archive to :class:`ValidationError`.

    The caller owns the returned handle — use it as a context manager. Opening
    from a path (rather than fully-buffered bytes) lets the worker read members
    off disk on demand instead of holding the whole archive in memory.
    """
    try:
        return zipfile.ZipFile(source)
    except zipfile.BadZipFile as exc:
        raise ValidationError("Uploaded file is not a valid .zip archive.") from exc


def plan_yolo_archive(
    zf: zipfile.ZipFile,
    *,
    max_uncompressed_bytes: int,
    max_items: int,
    image_extensions: list[str],
) -> list[YoloArchiveEntry]:
    """Plan a YOLO import from an open archive **without reading image bytes**.

    Pairs each image under an ``images/`` path with its ``labels/<stem>.txt``
    (by basename stem, ``images/foo.jpg`` ↔ ``labels/foo.txt``) and parses the
    label eagerly — labels are tiny. Images are left in the archive and recorded
    by member name for the caller to stream one at a time. An image with no
    matching label — or an empty label — yields an empty box list (a valid
    background image).

    Hardened against hostile archives: rejects absolute paths / ``..``
    traversal, and caps the total declared decompressed size and the image
    count. Raises :class:`ValidationError` on a cap breach or unsafe path.
    """
    exts = {e.lower() for e in image_extensions}
    infos = [i for i in zf.infolist() if not i.is_dir()]

    total_uncompressed = sum(i.file_size for i in infos)
    if total_uncompressed > max_uncompressed_bytes:
        raise ValidationError(
            f"Archive decompresses to {total_uncompressed} bytes, "
            f"over the {max_uncompressed_bytes}-byte limit."
        )

    labels: dict[str, bytes] = {}
    images: list[tuple[str, str]] = []  # (stem, member name)
    for info in infos:
        name = info.filename
        if _is_unsafe_path(name):
            raise ValidationError(f"Unsafe path in archive: {name!r}.")
        segments = posixpath.normpath(name).split("/")
        stem, ext = posixpath.splitext(posixpath.basename(name))
        ext = ext.lower()
        if "labels" in segments and ext == ".txt":
            labels[stem] = zf.read(info)
        elif "images" in segments and ext in exts:
            images.append((stem, name))

    if not images:
        raise ValidationError(
            "Archive contains no images under an 'images/' directory with a supported extension."
        )
    if len(images) > max_items:
        raise ValidationError(f"Archive has {len(images)} images, over the {max_items} limit.")

    entries: list[YoloArchiveEntry] = []
    for stem, member in images:
        label_bytes = labels.get(stem)
        boxes = parse_yolo_label(label_bytes.decode("utf-8")) if label_bytes else []
        entries.append(
            YoloArchiveEntry(
                member_name=member,
                filename=posixpath.basename(member),
                boxes=boxes,
            )
        )
    return entries


__all__ = ["YoloArchiveEntry", "open_yolo_archive", "parse_yolo_label", "plan_yolo_archive"]
