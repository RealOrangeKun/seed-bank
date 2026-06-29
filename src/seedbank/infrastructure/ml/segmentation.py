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


def get_session(model_name: str = _DEFAULT_MODEL) -> object:
    """Return the process-cached rembg session, building it once."""
    global _SESSION  # noqa: PLW0603 — process-wide singleton, guarded by a lock
    if _SESSION is not None:
        return _SESSION
    with _SESSION_LOCK:
        if _SESSION is None:
            from rembg import new_session

            providers = _providers()
            _SESSION = new_session(model_name, providers=providers)
            log.info("ml.segmentation.session_ready", model=model_name, providers=providers)
        return _SESSION


def segment_crop(
    image: Image.Image,
    *,
    background: tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    """Remove the background from ``image`` and composite over ``background``.

    Takes and returns an RGB ``PIL.Image``. On any failure the original image is
    returned unchanged so a flaky matting step degrades quality rather than
    failing the whole inference.
    """
    from PIL import Image as PILImage
    from rembg import remove

    try:
        rgba = remove(image.convert("RGBA"), session=get_session())
        if rgba.mode != "RGBA":
            rgba = rgba.convert("RGBA")
        canvas = PILImage.new("RGBA", rgba.size, (*background, 255))
        canvas.alpha_composite(rgba)
        return canvas.convert("RGB")
    except Exception as exc:
        log.warning("ml.segmentation.failed", error=repr(exc))
        return image.convert("RGB")


__all__ = ["get_session", "segment_crop"]
