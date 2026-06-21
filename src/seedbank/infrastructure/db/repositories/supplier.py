"""Supplier repository.

Combines the global catalog and a user's private suppliers behind a single
list method. The split is enforced by the partial uniques + CHECK on
`suppliers` (see models.py).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select

from seedbank.infrastructure.db.models import Supplier

from .base import Repository


class SupplierRepository(Repository[Supplier]):
    model = Supplier

    async def list_visible_to(self, user_id: UUID) -> list[Supplier]:
        """Globals + the user's own private rows. Soft-deleted rows excluded."""
        stmt = (
            select(Supplier)
            .where(
                Supplier.deleted_at.is_(None),
                Supplier.is_active.is_(True),
                or_(Supplier.is_global.is_(True), Supplier.created_by_user_id == user_id),
            )
            .order_by(Supplier.is_global.desc(), Supplier.name.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_visible(self, supplier_id: UUID, user_id: UUID) -> Supplier | None:
        stmt = select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.deleted_at.is_(None),
            or_(Supplier.is_global.is_(True), Supplier.created_by_user_id == user_id),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
