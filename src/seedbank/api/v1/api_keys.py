"""API-key endpoints — own-keys-only CRUD.

Each user manages their own keys. There is no admin endpoint to list other
users' keys (we never have the plaintext, and the prefix is the only safe
identifier — admins should revoke via DB if a leak is reported).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request, status

from seedbank.api.deps import ApiKeyServiceDep, CurrentUser
from seedbank.schemas.auth import ApiKeyCreateIn, ApiKeyOut

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("", response_model=list[ApiKeyOut])
async def list_keys(actor: CurrentUser, service: ApiKeyServiceDep) -> list[ApiKeyOut]:
    rows = await service.list_for_user(actor.id)
    # Plaintext key is never returned outside of creation.
    return [ApiKeyOut.model_validate(r) for r in rows]


@router.post("", response_model=ApiKeyOut, status_code=status.HTTP_201_CREATED)
async def create_key(
    payload: ApiKeyCreateIn,
    request: Request,
    actor: CurrentUser,
    service: ApiKeyServiceDep,
) -> ApiKeyOut:
    record, plaintext = await service.create(
        user_id=actor.id,
        name=payload.name,
        scopes=payload.scopes,
        expires_at=payload.expires_at,
        ip=request.client.host if request.client else None,
    )
    out = ApiKeyOut.model_validate(record)
    return out.model_copy(update={"key": plaintext})


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
