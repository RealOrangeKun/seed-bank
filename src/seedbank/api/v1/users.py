"""User-facing endpoints — `/me`, listing, role management."""

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

router = APIRouter(prefix="/users", tags=["users"])

AdminUser = Annotated[AuthenticatedUser, Depends(require_role(Role.ADMIN))]


@router.get("/me", response_model=MeOut)
async def get_me(actor: CurrentUser, users: UserRepoDep) -> MeOut:
    user = await users.get_by_id_active(actor.id)
    if user is None:
        raise NotFoundError("User not found.")
    return MeOut.model_validate(user)


@router.get("", response_model=list[UserListOut])
async def list_users(
    users: UserRepoDep,
    _admin: AdminUser,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[UserListOut]:
    rows = await users.list_active(limit=limit, offset=offset)
    return [UserListOut.model_validate(u) for u in rows]


@router.patch("/{user_id}/role", response_model=MeOut)
async def update_role(
    user_id: UUID,
    payload: RoleUpdateIn,
    request: Request,
    admin: AdminUser,
    service: AuthServiceDep,
) -> MeOut:
    user = await service.set_user_role(
        actor_id=admin.id,
        target_user_id=user_id,
        role=payload.role,
        ip=request.client.host if request.client else None,
    )
    return MeOut.model_validate(user)


__all__ = ["router"]
