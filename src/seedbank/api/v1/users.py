"""User-facing endpoints — ``/me``, listing, role management."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from seedbank.api.deps import (
    AuthServiceDep,
    CurrentUser,
    UserRepoDep,
    require_role,
)
from seedbank.core.exceptions import NotFoundError
from seedbank.domain.user import AuthenticatedUser, Role
from seedbank.schemas.auth import MeOut, RoleUpdateIn, UserListOut
from seedbank.schemas.common import Envelope, Page, paginate

router = APIRouter(prefix="/users", tags=["users"])

AdminUser = Annotated[AuthenticatedUser, Depends(require_role(Role.ADMIN))]


@router.get("/me", response_model=Envelope[MeOut])
async def get_me(actor: CurrentUser, users: UserRepoDep) -> Envelope[MeOut]:
    user = await users.get_by_id_active(actor.id)
    if user is None:
        raise NotFoundError("User not found.")
    return Envelope[MeOut](data=MeOut.model_validate(user))


@router.get("", response_model=Page[UserListOut])
async def list_users(
    users: UserRepoDep,
    _admin: AdminUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Page[UserListOut]:
    offset = (page - 1) * page_size
    rows = await users.list_active(limit=page_size, offset=offset)
    total = await users.count_active()
    items = [UserListOut.model_validate(u) for u in rows]
    return paginate(items, total=total, page=page, page_size=page_size)


@router.patch("/{user_id}/role", response_model=Envelope[MeOut])
async def update_role(
    user_id: UUID,
    payload: RoleUpdateIn,
    request: Request,
    admin: AdminUser,
    service: AuthServiceDep,
) -> Envelope[MeOut]:
    user = await service.set_user_role(
        actor_id=admin.id,
        target_user_id=user_id,
        role=payload.role,
        ip=request.client.host if request.client else None,
    )
    return Envelope[MeOut](data=MeOut.model_validate(user))


__all__ = ["router"]
