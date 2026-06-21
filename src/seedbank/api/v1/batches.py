"""``/api/v1/batches`` — read access to inference batches.

This is the polling endpoint clients hit after submitting to
``POST /api/v1/analyze``. ``GET /batches/{id}`` returns the full nested
graph (images → inferences → detections), eager-loaded in one query
chain so the JSON serialization doesn't trigger lazy IO.

Ownership rules: non-admin callers see only their own batches. Admin
can read any. ``BatchService.get_for_user`` enforces both — and raises
``NotFoundError`` rather than ``ForbiddenError`` on the cross-user case
so we don't leak existence.
"""

from __future__ import annotations

import csv
import io
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from seedbank.api.deps import AnalyticsServiceDep, BatchServiceDep, CurrentUser
from seedbank.schemas.analysis import (
    BatchBulkDeleteIn,
    BatchCompareIn,
    BatchCompareOut,
    BatchDeleteResult,
    BatchDetailOut,
    BatchOut,
    ImageUrlOut,
    SeedDetectionOut,
    ShareLinkOut,
)
from seedbank.schemas.common import Envelope, Page, paginate

router = APIRouter(prefix="/batches", tags=["batches"])

# Column order for CSV export — fixed so downstream spreadsheets/scripts can
# rely on it. Mirrors ``SeedDetectionOut`` field-for-field.
_EXPORT_COLUMNS: tuple[str, ...] = (
    "id",
    "seed_type_id",
    "quality",
    "confidence",
    "detection_confidence",
    "box_x_norm",
    "box_y_norm",
    "box_w_norm",
    "box_h_norm",
    "area_px",
    "width_px",
    "height_px",
    "aspect_ratio",
)


@router.get("", response_model=Page[BatchOut])
async def list_batches(
    actor: CurrentUser,
    service: BatchServiceDep,
    supplier_id: Annotated[UUID | None, Query()] = None,
    country_code: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Page[BatchOut]:
    rows, total = await service.list_for_user(
        user_id=actor.id,
        page=page,
        page_size=page_size,
        supplier_id=supplier_id,
        country_code=country_code,
    )
    # ``image_count`` isn't a column on ``scan_batches``; the service ships
    # it back alongside each batch (one grouped query). Patch it onto the
    # schema instance so the list view matches the analyze + detail shapes.
    items = [
        BatchOut.model_validate(batch).model_copy(update={"image_count": count})
        for batch, count in rows
    ]
    return paginate(items, total=total, page=page, page_size=page_size)


@router.get("/{batch_id}", response_model=Envelope[BatchDetailOut])
async def get_batch(
    batch_id: UUID,
    actor: CurrentUser,
    service: BatchServiceDep,
) -> Envelope[BatchDetailOut]:
    batch = await service.get_for_user(batch_id=batch_id, actor=actor)
    out = BatchDetailOut.model_validate(batch)
    # ``image_count`` isn't on the ORM — derive it from the eager-loaded
    # collection so the detail view is consistent with the analyze
    # response shape.
    out = out.model_copy(update={"image_count": len(out.images)})
    return Envelope[BatchDetailOut](data=out)


@router.get("/{batch_id}/image-urls", response_model=Envelope[list[ImageUrlOut]])
async def get_batch_image_urls(
    batch_id: UUID,
    actor: CurrentUser,
    service: BatchServiceDep,
) -> Envelope[list[ImageUrlOut]]:
    """Short-lived presigned URLs for the batch's images.

    The client pairs these with the normalized bounding boxes from
    ``GET /batches/{id}`` to render detections over the original image —
    the bytes are served straight from object storage, never proxied
    through the API.
    """
    urls = await service.image_urls_for_user(batch_id=batch_id, actor=actor)
    items = [ImageUrlOut.model_validate(u, from_attributes=True) for u in urls]
    return Envelope[list[ImageUrlOut]](data=items)


# ── Bulk delete ───────────────────────────────────────────────────────────────
# Declared before the ``/{batch_id}`` parametric routes. FastAPI matches by
# (method, path) so ``POST /batches/delete`` never collides with the GET
# parametric routes, but keeping the literal route first is the conventional
# guard against accidental shadowing if a POST /{batch_id} is ever added.


@router.post("/delete", response_model=Envelope[BatchDeleteResult])
async def bulk_delete_batches(
    payload: BatchBulkDeleteIn,
    actor: CurrentUser,
    service: BatchServiceDep,
) -> Envelope[BatchDeleteResult]:
    """Soft-delete up to 200 owned batches in one call.

    Best-effort: IDs the caller doesn't own or that are already deleted are
    skipped, and ``deleted`` reports how many actually took effect. Returns 200
    (not 204) because the count is the useful part of the response.
    """
    deleted = await service.bulk_delete_for_user(batch_ids=payload.batch_ids, actor=actor)
    return Envelope[BatchDeleteResult](data=BatchDeleteResult(deleted=deleted))


@router.post("/compare", response_model=Envelope[BatchCompareOut])
async def compare_batches(
    payload: BatchCompareIn,
    actor: CurrentUser,
    analytics: AnalyticsServiceDep,
) -> Envelope[BatchCompareOut]:
    """Side-by-side aggregate stats for 2–10 of the caller's batches.

    Owned batches come back in request order; any requested id the caller
    doesn't own is reported in ``missing`` instead of failing the request.
    """
    data = await analytics.compare(batch_ids=payload.batch_ids, user_id=actor.id)
    return Envelope[BatchCompareOut](data=data)


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_batch(
    batch_id: UUID,
    actor: CurrentUser,
    service: BatchServiceDep,
) -> None:
    """Soft-delete one batch the caller owns (admins: any).

    404 if it doesn't exist, isn't owned, or is already deleted — same
    non-enumeration rule as the read endpoints.
    """
    await service.delete_for_user(batch_id=batch_id, actor=actor)


@router.get(
    "/{batch_id}/export.csv",
    response_class=Response,
    responses={
        200: {
            "content": {"text/csv": {}},
            "description": "Every detection in the batch as CSV.",
        }
    },
)
async def export_batch_csv(
    batch_id: UUID,
    actor: CurrentUser,
    service: BatchServiceDep,
) -> Response:
    """Download every detection in the batch as a CSV file.

    Columns are fixed (:data:`_EXPORT_COLUMNS`) and rows are ordered by image
    then detection id, so re-exports diff cleanly. Decimals are emitted via the
    schema so they match the JSON wire format (``"0.9234"``, not a lossy float).
    """
    detections = await service.detections_for_export(batch_id=batch_id, actor=actor)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=_EXPORT_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for det in detections:
        row = SeedDetectionOut.model_validate(det).model_dump(mode="json")
        writer.writerow({col: row.get(col, "") for col in _EXPORT_COLUMNS})
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="batch-{batch_id}.csv"'},
    )


@router.get("/{batch_id}/export.json", response_model=Envelope[list[SeedDetectionOut]])
async def export_batch_json(
    batch_id: UUID,
    actor: CurrentUser,
    service: BatchServiceDep,
    response: Response,
) -> Envelope[list[SeedDetectionOut]]:
    """Download every detection in the batch as JSON.

    Same data and ordering as the CSV export, wrapped in the standard
    ``Envelope`` so it's consistent with the rest of the API. The
    ``Content-Disposition`` header nudges browsers to save it as a file.
    """
    detections = await service.detections_for_export(batch_id=batch_id, actor=actor)
    items = [SeedDetectionOut.model_validate(d) for d in detections]
    response.headers["Content-Disposition"] = f'attachment; filename="batch-{batch_id}.json"'
    return Envelope[list[SeedDetectionOut]](data=items)


@router.get(
    "/{batch_id}/images/{image_id}/annotated.png",
    response_class=Response,
    responses={
        200: {
            "content": {"image/png": {}},
            "description": "The scan image with detection boxes burned in.",
        }
    },
)
async def annotated_image(
    batch_id: UUID,
    image_id: UUID,
    actor: CurrentUser,
    service: BatchServiceDep,
) -> Response:
    """The original scan image with detection boxes drawn on, as a PNG.

    Boxes are colored by quality (good/bad/unclassified). Ownership-checked like
    every other batch read; 404 if the batch or image isn't the caller's.
    """
    png = await service.annotated_png_for_user(batch_id=batch_id, image_id=image_id, actor=actor)
    return Response(content=png, media_type="image/png")


@router.post("/{batch_id}/share", response_model=Envelope[ShareLinkOut])
async def create_share_link(
    batch_id: UUID,
    actor: CurrentUser,
    service: BatchServiceDep,
) -> Envelope[ShareLinkOut]:
    """Create (or rotate) a public read-only share link for an owned batch.

    Returns the opaque token and the relative public path the frontend turns
    into a shareable URL. Calling again rotates the token.
    """
    token = await service.create_share_link(batch_id=batch_id, actor=actor)
    return Envelope[ShareLinkOut](
        data=ShareLinkOut(
            batch_id=batch_id,
            share_token=token,
            share_path=f"/shared/{token}",
        )
    )


@router.delete("/{batch_id}/share", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_share_link(
    batch_id: UUID,
    actor: CurrentUser,
    service: BatchServiceDep,
) -> None:
    """Revoke the batch's share link — the public URL stops working."""
    await service.revoke_share_link(batch_id=batch_id, actor=actor)


__all__ = ["router"]
