"""``POST /api/v1/analyze`` — the unified inference entry point.

Accepts one or many image files via ``multipart/form-data``. The request
path stores them in MinIO, creates a ``scan_batch`` (``status=pending``),
and dispatches one Celery task per image. The handler returns
``HTTP 202 Accepted`` with the batch envelope so clients can poll
``GET /api/v1/batches/{id}`` for results — the queue boundary is the
whole point.

Per CLAUDE.md golden path:
    Don't add a new analyze endpoint variant. Extend the unified one.

Per-request ``model_id`` override is allowed for ``ai_developer`` and
``admin`` only; the service raises ``ForbiddenError`` for everyone else
and the global error handler maps that to a 403 Problem Details.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, Request, Response, UploadFile, status

from seedbank.api.deps import AnalysisServiceDep, CurrentUser
from seedbank.api.rate_limit import limiter
from seedbank.core.config import get_settings
from seedbank.schemas.analysis import BatchOut
from seedbank.schemas.common import Envelope
from seedbank.services.analysis_service import AnalyzeFile

router = APIRouter(prefix="/analyze", tags=["analyze"])


_LIMIT_ANALYZE = f"{get_settings().rate_limit_analyze_per_minute}/minute"


@router.post(
    "",
    response_model=Envelope[BatchOut],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit images (or a video) for detection + classification",
    description=(
        "Upload one or more images, **or** a single video. The server stores "
        "them in MinIO, creates a `scan_batch` (status=`pending`), and "
        "dispatches Celery tasks. The response is HTTP 202 with the batch "
        "envelope; clients poll `GET /api/v1/batches/{id}` for results.\n\n"
        "A video is sampled into frames and analyzed with the fast **YOLO** "
        "detector (one frame per sampled image); the `mode`, `model_id`, and "
        "`seed_type_id` knobs are ignored for video.\n\n"
        "The `model_id` override is restricted to `ai_developer` and `admin`."
    ),
)
@limiter.limit(_LIMIT_ANALYZE)
async def analyze(
    request: Request,
    response: Response,
    actor: CurrentUser,
    service: AnalysisServiceDep,
    files: Annotated[list[UploadFile], File(description="One or more images, or a single video")],
    supplier_id: Annotated[UUID | None, Form()] = None,
    seed_type_id: Annotated[UUID | None, Form()] = None,
    model_id: Annotated[UUID | None, Form()] = None,
    mode: Annotated[
        str | None,
        Form(
            pattern="^(fast|accurate)$",
            description=(
                "Pipeline selector: 'fast' = YOLO one-shot detector, "
                "'accurate' = Faster R-CNN two-stage. Unlike model_id this is "
                "open to all users. Ignored when model_id is set."
            ),
        ),
    ] = None,
    source: Annotated[
        str | None,
        Form(
            pattern="^(web|mobile|mobile_realtime)$",
            description=(
                "Client origin, used to split history per app: 'web', 'mobile', "
                "or 'mobile_realtime' (live-video frames, hidden from history). "
                "Omitted for direct/SDK callers → recorded as 'api'."
            ),
        ),
    ] = None,
    gps_lat: Annotated[Decimal | None, Form()] = None,
    gps_long: Annotated[Decimal | None, Form()] = None,
    country_code: Annotated[
        str | None,
        Form(min_length=2, max_length=2, pattern="^[A-Z]{2}$"),
    ] = None,
) -> Envelope[BatchOut]:
    # Read every file into memory up-front. The service-layer size cap
    # (``analyze_max_image_bytes``) is enforced per-file before MinIO is
    # touched, so the worst case is one over-sized payload sitting in RAM
    # for the duration of one request — bounded by the rate limiter and
    # by the max-files-per-request cap on top.
    payloads: list[AnalyzeFile] = []
    for f in files:
        data = await f.read()
        payloads.append(
            AnalyzeFile(
                filename=f.filename,
                content_type=f.content_type or "application/octet-stream",
                data=data,
            )
        )

    batch = await service.create_and_dispatch(
        actor=actor,
        files=payloads,
        supplier_id=supplier_id,
        seed_type_id=seed_type_id,
        model_id_override=model_id,
        mode=mode,
        source=source,
        gps_lat=gps_lat,
        gps_long=gps_long,
        country_code=country_code,
        ip=request.client.host if request.client else None,
    )

    # Standard REST hint for "we accepted, here's where to find the result".
    response.headers["Location"] = f"{get_settings().api_v1_prefix}/batches/{batch.id}"

    out = BatchOut.model_validate(batch)
    # ScanBatch ORM has no image_count column; the service ships it back
    # implicitly via len(payloads). For a video the frames don't exist yet
    # (the worker extracts them), so report 0 until polling fills it in.
    video_mimes = set(get_settings().analyze_allowed_video_mime_types)
    image_count = sum(1 for p in payloads if p.content_type not in video_mimes)
    out = out.model_copy(update={"image_count": image_count})
    return Envelope[BatchOut](data=out)


__all__ = ["router"]
