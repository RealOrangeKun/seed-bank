"""U2NET background removal (rembg) for Stage-2 crops.

The two-stage pipeline crops each detected seed from the source image and hands
it to an EfficientNet-B2 specialist. Cluttered backgrounds (trays, hands, other
seeds at the box edge) hurt the fine-grained defect classifier, so we segment
the seed first: run rembg's U2NET matting model, then composite the foreground
over a flat background before classification.

The rembg ``session`` is expensive to build (loads the U2NET ONNX graph) so it
is process-cached. It prefers the CUDA ONNX Runtime provider when available —
the heavy torch models already require a GPU box, and matting on CPU is the slow
path the user asked us to avoid — falling back to CPU only if CUDA isn't
present.

Heavy imports (rembg, onnxruntime, PIL, numpy) are deferred to first use so this
module stays importable in a segmentation-less context.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from seedbank.core.logging import get_logger

if TYPE_CHECKING:  # pragma: no cover
    from PIL import Image

log = get_logger(__name__)

_SESSION: object | None = None
# Sticky flag: once building the session fails (e.g. the U2NET weights can't be
# downloaded on an air-gapped host), don't retry on every crop — a 30s download
# timeout per seed would stall the whole batch. We attempt once, then fall back
# to the un-segmented crop for the rest of the process's life.
_SESSION_UNAVAILABLE = False
_SESSION_LOCK = threading.Lock()
_DEFAULT_MODEL = "u2net"


def _providers() -> list[str]:
    """ONNX Runtime providers, CUDA first when the GPU EP is installed."""
    try:
        import onnxruntime as ort

        available = set(ort.get_available_providers())
    except Exception:
        return ["CPUExecutionProvider"]
    ordered = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    return [p for p in ordered if p in available] or ["CPUExecutionProvider"]


def get_session(model_name: str = _DEFAULT_MODEL) -> object | None:
    """Return the process-cached rembg session, building it once.

    Returns ``None`` (and stays ``None``) if the session can't be built — the
    caller then skips segmentation instead of retrying the failing download.
    """
    global _SESSION, _SESSION_UNAVAILABLE  # noqa: PLW0603 — guarded singleton
    if _SESSION is not None:
        return _SESSION
    if _SESSION_UNAVAILABLE:
        return None
    with _SESSION_LOCK:
        if _SESSION is not None:
            return _SESSION
        if _SESSION_UNAVAILABLE:
            return None
        try:
            from rembg import new_session

            providers = _providers()
            _SESSION = new_session(model_name, providers=providers)
            log.info("ml.segmentation.session_ready", model=model_name, providers=providers)
            return _SESSION
        except Exception as exc:
            _SESSION_UNAVAILABLE = True
            log.warning("ml.segmentation.session_unavailable", error=repr(exc))
            return None


def segment_crop(
    image: Image.Image,
    *,
    background: tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    """Remove the background from ``image`` and composite over ``background``.

    Takes and returns an RGB ``PIL.Image``. If the U2NET session is unavailable
    or matting fails, the original image is returned unchanged so a flaky
    segmentation step degrades quality rather than failing the whole inference.
    """
    session = get_session()
    if session is None:
        return image.convert("RGB")

    from PIL import Image as PILImage
    from rembg import remove

    try:
        rgba = remove(image.convert("RGBA"), session=session)
        if rgba.mode != "RGBA":
            rgba = rgba.convert("RGBA")
        canvas = PILImage.new("RGBA", rgba.size, (*background, 255))
        canvas.alpha_composite(rgba)
        return canvas.convert("RGB")
    except Exception as exc:
        log.warning("ml.segmentation.failed", error=repr(exc))
        return image.convert("RGB")


__all__ = ["get_session", "segment_crop"]
