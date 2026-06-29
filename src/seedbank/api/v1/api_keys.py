"""API-key endpoints — own-keys-only CRUD.

Each user manages their own keys. There is no admin endpoint to list other
users' keys (we never have the plaintext, and the prefix is the only safe
identifier — admins should revoke via DB if a leak is reported).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, status

from seedbank.api.deps import ApiKeyServiceDep, CurrentUser
from seedbank.schemas.auth import ApiKeyCreateIn, ApiKeyOut
from seedbank.schemas.common import Envelope, Page, paginate

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("", response_model=Page[ApiKeyOut])
async def list_keys(
    actor: CurrentUser,
    service: ApiKeyServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Page[ApiKeyOut]:
    offset = (page - 1) * page_size
    rows, total = await service.list_for_user(actor.id, limit=page_size, offset=offset)
    # Plaintext key is never returned outside of creation.
    items = [ApiKeyOut.model_validate(r) for r in rows]
    return paginate(items, total=total, page=page, page_size=page_size)


@router.post(
    "",
    response_model=Envelope[ApiKeyOut],
    status_code=status.HTTP_201_CREATED,
)
async def create_key(
    payload: ApiKeyCreateIn,
    request: Request,
    actor: CurrentUser,
    service: ApiKeyServiceDep,
) -> Envelope[ApiKeyOut]:
    record, plaintext = await service.create(
        user_id=actor.id,
        name=payload.name,
        scopes=payload.scopes,
        expires_at=payload.expires_at,
        ip=request.client.host if request.client else None,
    )
    out = ApiKeyOut.model_validate(record).model_copy(update={"key": plaintext})
    return Envelope[ApiKeyOut](data=out)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_key(
    key_id: UUID,
    request: Request,
    actor: CurrentUser,
    service: ApiKeyServiceDep,
) -> None:
    await service.revoke(
        user_id=actor.id,
        key_id=key_id,
        ip=request.client.host if request.client else None,
    )


__all__ = ["router"]
