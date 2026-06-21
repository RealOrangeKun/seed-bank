"""Bootstrap operations — pure functions that seed catalog state.

These functions take the collaborators they need (an ``AsyncSession``,
a ``ClickHouseClient``, an ``AnalyticsRepository``) so they can be unit-
tested without spinning up a stack. CLI wrappers under ``scripts/``
assemble those collaborators and invoke these.

Organised by aggregate, not by ``script``: a CLI can mix-and-match (e.g.
``seed_dev`` calls ``users`` + ``seed_types`` + ``dwh``; ``init_clickhouse``
calls only ``dwh``).
"""

from __future__ import annotations

from .dwh import (
    apply_dwh_schema,
    bootstrap_clickhouse,
    ensure_clickhouse_database,
    mirror_seed_types_to_dwh,
)
from .seed_types import SeedTypeSpec, bootstrap_seed_types
from .suppliers import GlobalSupplierSpec, bootstrap_suppliers
from .users import DemoUserSpec, bootstrap_users

__all__ = [
    "DemoUserSpec",
    "GlobalSupplierSpec",
    "SeedTypeSpec",
    "apply_dwh_schema",
    "bootstrap_clickhouse",
    "bootstrap_seed_types",
    "bootstrap_suppliers",
    "bootstrap_users",
    "ensure_clickhouse_database",
    "mirror_seed_types_to_dwh",
]
