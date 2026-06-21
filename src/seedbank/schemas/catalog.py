"""Pydantic shapes for ``/api/v1/catalog`` — seed types + suppliers.

Reference data the frontend needs to render dropdowns instead of forcing
users to paste UUIDs:

- ``GET /seed-types`` is read-only (the catalog is curated via migrations
  + ``scripts/seed_dev.py``).
- Suppliers support full CRUD. Globals are admin-curated and visible to
  everyone; private suppliers are owned by a single user. The
  global-xor-owner split lives on the ORM (``suppliers.global_xor_owner``
  CHECK); the service enforces the authz half.

The ORM column for a supplier's free-form JSON is named ``metadata`` but
SQLAlchemy reserves that attribute name, so the model exposes it as
``supplier_metadata``. :class:`SupplierOut` validates from that attribute
(``validation_alias``) and serialises it back out as ``metadata`` so the
wire contract stays clean.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SeedTypeOut(BaseModel):
    """List entry for a :class:`SeedType` — the catalog dropdown source."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    display_name: str
    description: str | None = None
    default_confidence_threshold: Decimal


class SupplierOut(BaseModel):
    """List + detail response for a :class:`Supplier`."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    is_global: bool
    is_active: bool
    created_by_user_id: UUID | None = None
    # ORM attr is ``supplier_metadata`` (column ``metadata``). Read from that
    # exact attribute — NOT "metadata", which on a SQLAlchemy model resolves to
    # the declarative ``Base.metadata`` registry, not the JSON column — and
    # serialise it back out under the clean wire name ``metadata``.
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias="supplier_metadata",
        serialization_alias="metadata",
    )
    created_at: datetime
    updated_at: datetime


class SupplierCreateIn(BaseModel):
    """Request body for ``POST /suppliers``."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    is_global: bool = False
    metadata: dict[str, Any] | None = None


class SupplierUpdateIn(BaseModel):
    """Request body for ``PATCH /suppliers/{id}`` — all fields optional."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=160)
    is_active: bool | None = None
    metadata: dict[str, Any] | None = None


__all__ = [
    "SeedTypeOut",
    "SupplierCreateIn",
    "SupplierOut",
    "SupplierUpdateIn",
]
