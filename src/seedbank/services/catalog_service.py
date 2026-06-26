"""Catalog service — reference data for ``/api/v1/catalog``.

Two aggregates behind one service because the frontend treats them as the
same concern ("things I pick from a dropdown"):

- **Seed types** are read-only here. The catalog is curated via migrations
  and ``scripts/seed_dev.py``; the API only lists it.
- **Suppliers** support full CRUD. The visibility model is the same one
  enforced on the ORM (``suppliers.global_xor_owner``):

    * *global*  — ``is_global=True``, ``created_by_user_id IS NULL``,
      admin-only to mutate, visible to everyone.
    * *private* — ``is_global=False``, owned by one user, mutable by the
      owner (or an admin).

Authorization for the *route* (must be ``ai_developer`` or ``admin``) is
the router's job via ``require_role``; the finer-grained "is this actor
allowed to touch *this* supplier" check lives here so the rule is tested
without a transport. The service raises domain errors only — never
``HTTPException``.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy.exc import IntegrityError

from seedbank.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from seedbank.core.ids import uuid7
from seedbank.core.logging import get_logger
from seedbank.infrastructure.db.models import Supplier

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from seedbank.domain.user import AuthenticatedUser
    from seedbank.infrastructure.db.models import SeedType
    from seedbank.infrastructure.db.repositories import (
        SeedTypeRepository,
        SupplierRepository,
    )

log = get_logger(__name__)

_SLUG_SUB = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    """Lower-case, dash-separated slug body. Uniqueness is added by the
    caller (suffixing a uuid7 hex), so this only needs to be readable, not
    globally unique on its own."""
    return _SLUG_SUB.sub("-", name.strip().lower()).strip("-") or "supplier"


class CatalogService:
    """Use cases for ``/api/v1/catalog`` (seed types + suppliers)."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        seed_types: SeedTypeRepository,
        suppliers: SupplierRepository,
    ) -> None:
        self.session = session
        self.seed_types = seed_types
        self.suppliers = suppliers

    # ── seed types ──────────────────────────────────────────────────────────

    async def list_seed_types(self) -> list[SeedType]:
        """The full seed-type catalog (curated reference data)."""
        return await self.seed_types.list_all()

    # ── suppliers ───────────────────────────────────────────────────────────

    async def list_suppliers(self, actor: AuthenticatedUser) -> list[Supplier]:
        """Globals + the actor's own private suppliers (active, not deleted)."""
        return await self.suppliers.list_visible_to(actor.id)

    async def create_supplier(
        self,
        *,
        actor: AuthenticatedUser,
        name: str,
        is_global: bool,
        metadata: dict[str, Any] | None,
    ) -> Supplier:
        """Create a global (admin-only) or private supplier.

        The global-xor-owner invariant is honoured up front:
        ``is_global`` ⇒ ``created_by_user_id IS NULL`` (and admin-only);
        otherwise the actor owns the row. Slug is made globally unique by
        suffixing a uuid7 hex. Unique-slug races translate to
        :class:`ConflictError`.
        """
        if is_global and not actor.is_admin:
            raise ForbiddenError("Only admins can create global suppliers.")

        created_by_user_id = None if is_global else actor.id
        supplier = Supplier(
            id=uuid7(),
            name=name,
            slug=f"{_slugify(name)}-{uuid7().hex[:8]}",
            is_global=is_global,
            created_by_user_id=created_by_user_id,
            is_active=True,
            supplier_metadata=metadata,
        )
        try:
            await self.suppliers.add(supplier)
            await self.session.commit()
        except IntegrityError as exc:
            # Slug collision or a partial-unique name clash within the
            # visibility scope. Either way the caller picked a name/slug
            # that's already taken.
            await self.session.rollback()
            raise ConflictError(f"Supplier name {name!r} already exists.") from exc
        # Populate DB-side defaults (created_at/updated_at) before the router
        # serialises SupplierOut: without it, Pydantic's attribute read triggers
        # a lazy refresh outside the async context (MissingGreenlet). Same
        # pattern as model_registry_service.
        await self.session.refresh(supplier)
        log.info(
            "supplier.created",
            supplier_id=str(supplier.id),
            is_global=is_global,
            actor_id=str(actor.id),
        )
        return supplier

    async def update_supplier(
        self,
        *,
        actor: AuthenticatedUser,
        supplier_id: UUID,
        name: str | None,
        is_active: bool | None,
        metadata: dict[str, Any] | None,
    ) -> Supplier:
        """Patch the provided fields on a supplier the actor may mutate.

        Only non-``None`` fields are applied (PATCH semantics). Mutation
        authz: globals are admin-only; private rows are mutable by the owner
        or an admin. Unique-name violations translate to
        :class:`ConflictError`.
        """
        supplier = await self._load_mutable(actor=actor, supplier_id=supplier_id)

        if name is not None:
            supplier.name = name
        if is_active is not None:
            supplier.is_active = is_active
        if metadata is not None:
            supplier.supplier_metadata = metadata

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(
                f"Supplier name {name!r} already exists."
                if name is not None
                else "Supplier update violates a uniqueness constraint."
            ) from exc
        # See create_supplier: refresh so updated_at/created_at are loaded before
        # the router validates SupplierOut.
        await self.session.refresh(supplier)
        log.info(
            "supplier.updated",
            supplier_id=str(supplier.id),
            actor_id=str(actor.id),
        )
        return supplier

    async def soft_delete_supplier(
        self,
        *,
        actor: AuthenticatedUser,
        supplier_id: UUID,
    ) -> None:
        """Soft-delete a supplier the actor may mutate (stamps ``deleted_at``)."""
        supplier = await self._load_mutable(actor=actor, supplier_id=supplier_id)
        supplier.deleted_at = datetime.now(UTC)
        await self.session.commit()
        log.info(
            "supplier.deleted",
            supplier_id=str(supplier.id),
            actor_id=str(actor.id),
        )

    async def _load_mutable(
        self,
        *,
        actor: AuthenticatedUser,
        supplier_id: UUID,
    ) -> Supplier:
        """Load a visible supplier and assert the actor may mutate it.

        ``NotFoundError`` when the row is absent/invisible; ``ForbiddenError``
        when it's visible but the actor isn't its owner (private) or an admin
        (global). Globals are visible to everyone but mutable by admins only.
        """
        supplier = await self.suppliers.get_visible(supplier_id, actor.id)
        if supplier is None:
            raise NotFoundError("Supplier not found.")
        if actor.is_admin:
            return supplier
        if supplier.is_global:
            raise ForbiddenError("Only admins can modify global suppliers.")
        if supplier.created_by_user_id != actor.id:
            raise ForbiddenError("You do not own this supplier.")
        return supplier


__all__ = ["CatalogService"]
