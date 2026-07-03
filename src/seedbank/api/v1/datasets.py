"""``/api/v1/datasets`` — registry of frozen eval substrates.

Datasets feed the experiment runner. They are managed by AI developers
(role ``ai_developer``); end-users have no read access. Admins satisfy the
role check implicitly via ``require_role``.

Items are append-only: an experiment's results reference
``dataset_item_id`` directly, so removing an item would orphan history.
The whole dataset can be soft-deleted, but that lives in a future cleanup
operation; the MVP exposes create/list/read + bulk-add only.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from seedbank.api.deps import (
    CurrentUser,
    DatasetServiceDep,
    require_role,
)
from seedbank.domain.user import Role
from seedbank.schemas.common import Envelope, Page, paginate
from seedbank.schemas.dataset import (
    DatasetCreateIn,
    DatasetImportIn,
    DatasetImportOut,
    DatasetItemOut,
    DatasetItemsAddedOut,
    DatasetItemsBulkIn,
    DatasetOut,
    DatasetUploadUrlIn,
    DatasetUploadUrlOut,
)

router = APIRouter(prefix="/datasets", tags=["datasets"])

_AI_GATE = Depends(require_role(Role.AI_DEVELOPER))


@router.post(
    "",
    response_model=Envelope[DatasetOut],
    status_code=201,
    dependencies=[_AI_GATE],
)
async def create_dataset(
    body: DatasetCreateIn,
    actor: CurrentUser,
    service: DatasetServiceDep,
) -> Envelope[DatasetOut]:
    ds = await service.create(actor=actor, name=body.name, description=body.description)
    out = DatasetOut.model_validate(ds)
    return Envelope[DatasetOut](data=out)


@router.get("", response_model=Page[DatasetOut], dependencies=[_AI_GATE])
async def list_datasets(
    service: DatasetServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Page[DatasetOut]:
    annotated, total = await service.list_with_counts(page=page, page_size=page_size)
    items = [
        DatasetOut.model_validate(ds).model_copy(update={"item_count": cnt})
        for ds, cnt in annotated
    ]
    return paginate(items, total=total, page=page, page_size=page_size)


@router.get(
    "/{dataset_id}",
    response_model=Envelope[DatasetOut],
    dependencies=[_AI_GATE],
)
async def get_dataset(
    dataset_id: UUID,
    service: DatasetServiceDep,
) -> Envelope[DatasetOut]:
    ds, cnt = await service.get_with_count(dataset_id)
    out = DatasetOut.model_validate(ds).model_copy(update={"item_count": cnt})
    return Envelope[DatasetOut](data=out)


@router.post(
    "/{dataset_id}/items",
    response_model=Envelope[DatasetItemsAddedOut],
    status_code=201,
    dependencies=[_AI_GATE],
)
async def add_items(
    dataset_id: UUID,
    body: DatasetItemsBulkIn,
    service: DatasetServiceDep,
) -> Envelope[DatasetItemsAddedOut]:
    n = await service.add_items(dataset_id=dataset_id, items=body.items)
    return Envelope[DatasetItemsAddedOut](data=DatasetItemsAddedOut(added=n))


@router.post(
    "/{dataset_id}/upload-url",
    response_model=Envelope[DatasetUploadUrlOut],
    status_code=201,
    dependencies=[_AI_GATE],
)
async def create_upload_url(
    dataset_id: UUID,
    body: DatasetUploadUrlIn,
    service: DatasetServiceDep,
) -> Envelope[DatasetUploadUrlOut]:
    """Mint a presigned PUT URL so the browser can upload an image directly to
    MinIO, then register it via ``POST /datasets/{id}/items`` with the returned
    ``storage_key``. Keeps image bytes off the API process."""
    url, key = await service.create_upload_url(
        dataset_id=dataset_id,
        filename=body.filename,
        content_type=body.content_type,
    )
    return Envelope[DatasetUploadUrlOut](data=DatasetUploadUrlOut(upload_url=url, storage_key=key))


@router.post(
    "/{dataset_id}/import",
    response_model=Envelope[DatasetImportOut],
    status_code=202,
    dependencies=[_AI_GATE],
)
async def import_yolo(
    dataset_id: UUID,
    body: DatasetImportIn,
    service: DatasetServiceDep,
) -> Envelope[DatasetImportOut]:
    """Import a YOLO-labelled dataset from a previously-uploaded ``.zip``
    (``images/`` + ``labels/``). The archive must already be in MinIO (via
    ``POST /datasets/{id}/upload-url`` then a presigned PUT). Unpacking runs in
    a background worker; poll ``GET /datasets/{id}`` for the growing item
    count."""
    await service.dispatch_yolo_import(
        dataset_id=dataset_id,
        zip_storage_key=body.zip_storage_key,
    )
    return Envelope[DatasetImportOut](data=DatasetImportOut(dispatched=True))


@router.get(
    "/{dataset_id}/items",
    response_model=Page[DatasetItemOut],
    dependencies=[_AI_GATE],
)
async def list_items(
    dataset_id: UUID,
    service: DatasetServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 100,
) -> Page[DatasetItemOut]:
    rows, total = await service.list_items(dataset_id=dataset_id, page=page, page_size=page_size)
    items = [DatasetItemOut.model_validate(r) for r in rows]
    return paginate(items, total=total, page=page, page_size=page_size)


__all__ = ["router"]
