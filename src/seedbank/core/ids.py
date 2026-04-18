"""UUIDv7 helpers.

Postgres primary keys use UUIDv7 — sortable by creation time, globally unique,
and cheaper on B-tree inserts than UUIDv4. Never use `uuid4()` for PKs.
"""

from __future__ import annotations

from uuid import UUID

# The PyPI package `uuid7` installs the module as `uuid_extensions`.
from uuid_extensions import uuid7 as _uuid7


def uuid7() -> UUID:
    """Return a fresh UUIDv7."""
    return UUID(str(_uuid7()))
