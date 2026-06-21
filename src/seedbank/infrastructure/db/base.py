"""SQLAlchemy declarative base + reusable mixins.

`Base` is the single MetaData target Alembic introspects. Mixins provide the
cross-cutting `created_at` / `updated_at` / `deleted_at` columns the schema
spec mandates.

A standard naming convention is registered so generated index/constraint names
are stable across environments — this matters for Alembic autogenerate diffs
and for production rollbacks.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Stable, deterministic constraint/index names. Alembic compares these on
# autogenerate; without a convention, every developer's box invents new ones.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Project-wide declarative base."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """Mixin for created_at / updated_at columns.

    Both are `TIMESTAMP WITH TIME ZONE`, defaulted at the DB layer so a missing
    INSERT default in app code can never produce a NULL value.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SoftDeleteMixin:
    """Mixin for `deleted_at`. Only user-visible aggregates use this.

    The repository layer is responsible for filtering `deleted_at IS NULL`
    on default reads. Hard delete is forbidden on these tables.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
