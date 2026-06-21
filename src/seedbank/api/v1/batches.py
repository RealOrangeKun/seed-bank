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

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from seedbank.api.deps import BatchServiceDep, CurrentUser
from seedbank.schemas.analysis import BatchDetailOut, BatchOut, ImageUrlOut
from seedbank.schemas.common import Envelope, Page, paginate

router = APIRouter(prefix="/batches", tags=["batches"])


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


__all__ = ["router"]
