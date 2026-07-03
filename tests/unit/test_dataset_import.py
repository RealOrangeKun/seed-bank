"""Unit tests for the YOLO dataset-import helpers."""

from __future__ import annotations

import io
import zipfile

import pytest

from seedbank.core.exceptions import ValidationError
from seedbank.services.dataset_import import (
    YoloArchiveEntry,
    open_yolo_archive,
    parse_yolo_label,
    plan_yolo_archive,
)

pytestmark = pytest.mark.unit


def _zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


_EXTS = [".jpg", ".jpeg", ".png", ".webp"]


# ── parse_yolo_label ───────────────────────────────────────────────────────


def test_parse_converts_center_to_corner() -> None:
    boxes = parse_yolo_label("0 0.5 0.5 0.2 0.4")
    assert len(boxes) == 1
    box = boxes[0]
    # x = xc - w/2 = 0.4 ; y = yc - h/2 = 0.3
    assert box["x"] == pytest.approx(0.4)
    assert box["y"] == pytest.approx(0.3)
    assert box["w"] == pytest.approx(0.2)
    assert box["h"] == pytest.approx(0.4)
    assert box["label"] == "0"


def test_parse_preserves_class_id_as_label() -> None:
    boxes = parse_yolo_label("33 0.5 0.5 0.1 0.1")
    assert boxes[0]["label"] == "33"


def test_parse_empty_or_blank_is_no_boxes() -> None:
    assert parse_yolo_label("") == []
    assert parse_yolo_label("   \n\n  \n") == []


def test_parse_multiple_lines() -> None:
    boxes = parse_yolo_label("0 0.5 0.5 0.2 0.2\n1 0.25 0.25 0.1 0.1\n")
    assert len(boxes) == 2


def test_parse_clamps_corner_to_zero_for_edge_box() -> None:
    # A box centered near the left edge would produce a slightly negative x.
    boxes = parse_yolo_label("0 0.05 0.5 0.2 0.2")
    assert boxes[0]["x"] == 0.0


def test_parse_polygon_segmentation_reduces_to_bbox() -> None:
    # class + a triangle: (0.2,0.2), (0.6,0.2), (0.4,0.8) → bbox (0.2,0.2,0.4,0.6).
    boxes = parse_yolo_label("38 0.2 0.2 0.6 0.2 0.4 0.8")
    assert len(boxes) == 1
    box = boxes[0]
    assert box["x"] == pytest.approx(0.2)
    assert box["y"] == pytest.approx(0.2)
    assert box["w"] == pytest.approx(0.4)
    assert box["h"] == pytest.approx(0.6)
    assert box["label"] == "38"


def test_parse_mixed_detection_and_polygon_lines() -> None:
    # A real Roboflow export can mix a 5-field box with a polygon line.
    boxes = parse_yolo_label("0 0.5 0.5 0.2 0.2\n1 0.1 0.1 0.3 0.1 0.2 0.4")
    assert len(boxes) == 2


@pytest.mark.parametrize(
    "bad",
    [
        "0 0.5 0.5 0.2",  # too few fields
        "0 0.5 0.5 0.2 0.2 0.1",  # 6 fields — neither detection nor a polygon
        "a 0.5 0.5 0.2 0.2",  # non-numeric class id
        "0 1.5 0.5 0.2 0.2",  # xc out of range
        "0 0.5 0.5 0.0 0.2",  # zero width
    ],
)
def test_parse_rejects_malformed(bad: str) -> None:
    with pytest.raises(ValidationError):
        parse_yolo_label(bad)


# ── plan_yolo_archive ──────────────────────────────────────────────────────


def _plan(
    zip_bytes: bytes, *, max_items: int = 100, max_bytes: int = 10_000_000
) -> list[YoloArchiveEntry]:
    with open_yolo_archive(io.BytesIO(zip_bytes)) as zf:
        return plan_yolo_archive(
            zf,
            max_uncompressed_bytes=max_bytes,
            max_items=max_items,
            image_extensions=_EXTS,
        )


def test_archive_pairs_image_with_label() -> None:
    archive = _zip(
        {
            "images/a.jpg": b"img-a",
            "labels/a.txt": b"0 0.5 0.5 0.2 0.2",
        }
    )
    entries = _plan(archive)
    assert len(entries) == 1
    assert entries[0].filename == "a.jpg"
    assert len(entries[0].boxes) == 1
    # Image bytes are read lazily from the archive by member name.
    with open_yolo_archive(io.BytesIO(archive)) as zf:
        assert zf.read(entries[0].member_name) == b"img-a"


def test_archive_image_without_label_is_background() -> None:
    entries = _plan(_zip({"images/b.png": b"img-b"}))
    assert len(entries) == 1
    assert entries[0].boxes == []


def test_archive_empty_label_is_background() -> None:
    entries = _plan(_zip({"images/c.jpg": b"img-c", "labels/c.txt": b""}))
    assert entries[0].boxes == []


def test_archive_multi_dot_stem_pairs_correctly() -> None:
    # Roboflow-style names with dots in the stem must still pair.
    name = "20220510_102500_jpg.rf.2BBT8e6SNIvOFoh0grBc"
    entries = _plan(_zip({f"images/{name}.jpg": b"i", f"labels/{name}.txt": b"0 0.5 0.5 0.1 0.1"}))
    assert len(entries) == 1
    assert len(entries[0].boxes) == 1


def test_archive_rejects_zip_slip() -> None:
    with pytest.raises(ValidationError):
        _plan(_zip({"../evil.jpg": b"x", "images/a.jpg": b"i"}))


def test_archive_rejects_too_many_items() -> None:
    with pytest.raises(ValidationError):
        _plan(_zip({"images/a.jpg": b"i", "images/b.jpg": b"j"}), max_items=1)


def test_archive_rejects_zip_bomb_by_size() -> None:
    with pytest.raises(ValidationError):
        _plan(_zip({"images/a.jpg": b"a lot of bytes here"}), max_bytes=1)


def test_archive_rejects_no_images() -> None:
    with pytest.raises(ValidationError):
        _plan(_zip({"labels/a.txt": b"0 0.5 0.5 0.1 0.1"}))


def test_archive_rejects_bad_zip() -> None:
    with pytest.raises(ValidationError):
        open_yolo_archive(io.BytesIO(b"this is not a zip"))
