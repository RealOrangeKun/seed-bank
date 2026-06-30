"""drop api_keys table

Removes the personal API-key feature. Programmatic authentication via
``X-API-Key`` is gone — every actor now authenticates with a JWT bearer token
(password or OAuth login). The router, service, repository, schemas, ORM model
and the ``X-API-Key`` resolution path were all deleted alongside this migration.

``downgrade`` recreates the table exactly as ``0001_baseline.py`` defined it
(referencing the existing ``users`` table).

Hand-rolled. Mirrors ``0001_baseline.py``.

Revision ID: 0005_drop_api_keys
Revises: 0004_drop_traffic_mlflow
Create Date: 2026-06-30 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_drop_api_keys"
down_revision = "0004_drop_traffic_mlflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # drop_table cascades the table's indexes, FK and unique constraint.
    op.drop_table("api_keys")


def downgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("prefix", sa.String(16), nullable=False),
        sa.Column(
            "scopes",
            postgresql.ARRAY(sa.String(64)),
            nullable=False,
            server_default=sa.text("'{}'::varchar[]"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("key_hash", name="uq_api_keys_key_hash"),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index("ix_api_keys_prefix", "api_keys", ["prefix"])
