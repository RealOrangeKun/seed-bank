"""Unit tests for the YOLO video annotator in ``workers.tasks.analyze_video``.

``_detections_from_result`` is a pure pixel→normalized mapping (no torch).
``_annotate_video`` is exercised with a *fake* YOLO whose ``predict`` yields
frames, so we test the streaming draw+encode path without real weights — it
still needs OpenCV + imageio-ffmpeg, so it skips when those aren't installed
(the lean typecheck env) and runs in CI / the inference image.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

np = pytest.importorskip("numpy")


class _FakeArray:
    """Mimics a torch tensor's ``.cpu().numpy()`` chain over a numpy array."""

    def __init__(self, arr: object) -> None:
        self._arr = arr

    def cpu(self) -> _FakeArray:
        return self

    def numpy(self) -> object:
        return self._arr


class _FakeBoxes:
    def __init__(self, xyxy: object, conf: object, cls: object) -> None:
        self.xyxy = _FakeArray(xyxy)
        self.conf = _FakeArray(conf)
        self.cls = _FakeArray(cls)
        self._n = len(xyxy)  # type: ignore[arg-type]

    def __len__(self) -> int:
        return self._n


class _FakeResult:
    def __init__(self, boxes: _FakeBoxes | None, *, size: tuple[int, int]) -> None:
        self.boxes = boxes
        self.names = {0: "GOOD_GARLIC", 1: "BAD_GARLIC"}
        h, w = size
        self.orig_shape = (h, w)
        self._size = size

    def plot(self) -> object:
        h, w = self._size
        return np.full((h, w, 3), (40, 120, 80), dtype=np.uint8)


def test_detections_from_result_normalizes_boxes() -> None:
    from seedbank.workers.tasks.analyze_video import _detections_from_result

    # One 50×50 box at (10,20) in a 100×200 (h×w) frame.
    boxes = _FakeBoxes(
        xyxy=np.array([[10.0, 20.0, 60.0, 70.0]]),
        conf=np.array([0.9]),
        cls=np.array([0]),
    )
    r = _FakeResult(boxes, size=(100, 200))
    dets = _detections_from_result(r)
    assert len(dets) == 1
    d = dets[0]
    assert d.class_name == "GOOD_GARLIC"
    assert d.confidence == pytest.approx(0.9)
    assert d.bbox.x == pytest.approx(10 / 200)
    assert d.bbox.y == pytest.approx(20 / 100)
    assert d.bbox.w == pytest.approx(50 / 200)
    assert d.bbox.h == pytest.approx(50 / 100)


def test_detections_from_result_empty() -> None:
    from seedbank.workers.tasks.analyze_video import _detections_from_result

    assert _detections_from_result(_FakeResult(None, size=(10, 10))) == []


def _real_mp4_bytes(*, frames: int, fps: float, size: tuple[int, int]) -> bytes:
    """A real (cv2-decodable) mp4 so the annotator's fps/frame-count probe
    succeeds; the fake YOLO ignores its contents."""
    import tempfile
    from pathlib import Path

    import cv2

    w, h = size
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        path = tmp.name
    try:
        writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
        for i in range(frames):
            writer.write(np.full((h, w, 3), (i * 8 % 255, 100, 150), dtype=np.uint8))
        writer.release()
        return Path(path).read_bytes()
    finally:
        Path(path).unlink(missing_ok=True)


def test_annotate_video_encodes_h264_and_collects_detections() -> None:
    pytest.importorskip("cv2")
    pytest.importorskip("imageio")
    pytest.importorskip("imageio_ffmpeg")
    from seedbank.workers.tasks.analyze_video import _annotate_video

    class _FakeYolo:
        def predict(self, **_kwargs: object) -> list[_FakeResult]:
            boxes = _FakeBoxes(
                xyxy=np.array([[1.0, 1.0, 9.0, 9.0]]),
                conf=np.array([0.8]),
                cls=np.array([1]),
            )
            return [_FakeResult(boxes, size=(48, 64)) for _ in range(6)]

    result = _annotate_video(
        _FakeYolo(),
        _real_mp4_bytes(frames=6, fps=10.0, size=(64, 48)),
        conf=0.5,
        iou=0.7,
        imgsz=64,
        max_frames=300,
        max_stats_frames=40,
    )
    assert result is not None
    assert result.frame_count == 6
    assert result.width == 64 and result.height == 48
    assert result.video_mp4[:4] == b"\x00\x00\x00\x18" or result.video_mp4[4:8] == b"ftyp"
    assert result.poster_jpeg[:3] == b"\xff\xd8\xff"
    assert len(result.detections) >= 1
    assert result.detections[0].class_name == "BAD_GARLIC"
