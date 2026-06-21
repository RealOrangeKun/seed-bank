"""``/api/v1`` catalog — reference data the frontend renders as dropdowns.

Two read endpoints (seed types, suppliers) plus full supplier CRUD. The
router has no prefix because the two resources live at sibling top-level
paths (``/seed-types``, ``/suppliers``); using full paths keeps that
explicit.

Route-level authz:

- reads require any authenticated actor (``CurrentUser``);
- writes are gated to ``ai_developer`` (admins satisfy ``require_role``
  implicitly). Per-resource authz — global suppliers are admin-only,
  private suppliers are owner-only — lives in :class:`CatalogService`.

Routers do only: parse → call service → wrap.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response

from seedbank.api.deps import (
    CatalogServiceDep,
    CurrentUser,
    current_user,
    require_role,
)
from seedbank.domain.user import Role
from seedbank.schemas.catalog import (
    SeedTypeOut,
    SupplierCreateIn,
    SupplierOut,
    SupplierUpdateIn,
)
from seedbank.schemas.common import Envelope

router = APIRouter(tags=["catalog"])

_AI_GATE = Depends(require_role(Role.AI_DEVELOPER))
# Any authenticated actor — applied as a route-level dependency where the
# handler doesn't otherwise need the ``AuthenticatedUser`` value.
_AUTH_GATE = Depends(current_user)


@router.get(
    "/seed-types",
    response_model=Envelope[list[SeedTypeOut]],
    dependencies=[_AUTH_GATE],
)
async def list_seed_types(
    service: CatalogServiceDep,
) -> Envelope[list[SeedTypeOut]]:
    rows = await service.list_seed_types()
    items = [SeedTypeOut.model_validate(r) for r in rows]
    return Envelope[list[SeedTypeOut]](data=items)


@router.get("/suppliers", response_model=Envelope[list[SupplierOut]])
async def list_suppliers(
    actor: CurrentUser,
    service: CatalogServiceDep,
) -> Envelope[list[SupplierOut]]:
    rows = await service.list_suppliers(actor)
    items = [SupplierOut.model_validate(r) for r in rows]
    return Envelope[list[SupplierOut]](data=items)


@router.post(
    "/suppliers",
    response_model=Envelope[SupplierOut],
    status_code=201,
    dependencies=[_AI_GATE],
)
async def create_supplier(
    body: SupplierCreateIn,
    actor: CurrentUser,
    service: CatalogServiceDep,
) -> Envelope[SupplierOut]:
    supplier = await service.create_supplier(
        actor=actor,
        name=body.name,
        is_global=body.is_global,
        metadata=body.metadata,
    )
    return Envelope[SupplierOut](data=SupplierOut.model_validate(supplier))


@router.patch(
    "/suppliers/{supplier_id}",
    response_model=Envelope[SupplierOut],
    dependencies=[_AI_GATE],
)
async def update_supplier(
    supplier_id: UUID,
    body: SupplierUpdateIn,
    actor: CurrentUser,
    service: CatalogServiceDep,
) -> Envelope[SupplierOut]:
    supplier = await service.update_supplier(
        actor=actor,
        supplier_id=supplier_id,
        name=body.name,
        is_active=body.is_active,
        metadata=body.metadata,
    )
    return Envelope[SupplierOut](data=SupplierOut.model_validate(supplier))


@router.delete(
    "/suppliers/{supplier_id}",
    status_code=204,
    dependencies=[_AI_GATE],
)
async def delete_supplier(
    supplier_id: UUID,
    actor: CurrentUser,
    service: CatalogServiceDep,
) -> Response:
    await service.soft_delete_supplier(actor=actor, supplier_id=supplier_id)
    return Response(status_code=204)


__all__ = ["router"]
