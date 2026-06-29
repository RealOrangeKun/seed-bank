"""batch source: mobile + mobile_realtime

Adds two values to the ``batch_source`` enum so the platform can tell mobile
scans apart from web scans (the history views filter on this), and so the
mobile realtime scanner's per-frame batches can be tagged ``mobile_realtime``
and hidden from history.

``ALTER TYPE ... ADD VALUE`` is supported inside a transaction on PostgreSQL
12+ as long as the new value isn't *used* in the same transaction (it isn't
here). ``IF NOT EXISTS`` makes the migration idempotent.

Hand-rolled to match ``infrastructure/db/enums.py::BatchSource``.

Revision ID: 0003_batch_source_mobile
Revises: 0002_batch_share_token
Create Date: 2026-06-29 00:00:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "0003_batch_source_mobile"
down_revision = "0002_batch_share_token"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE batch_source ADD VALUE IF NOT EXISTS 'mobile'")
    op.execute("ALTER TYPE batch_source ADD VALUE IF NOT EXISTS 'mobile_realtime'")


def downgrade() -> None:
    # PostgreSQL can't drop a value from an enum without recreating the type and
    # rewriting every dependent column. The added values are harmless if unused,
    # so the downgrade is intentionally a no-op (forward-only enum growth).
    pass
