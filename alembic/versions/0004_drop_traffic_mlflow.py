"""drop traffic_splits + mlflow_run_id columns

Removes the A/B traffic-splits feature and the dormant MLflow tracking columns:

* ``traffic_splits`` table (live A/B routing) — model selection now resolves the
  ``production`` model directly via ``services/model_resolver.ModelResolver``.
* ``model_artifacts.mlflow_run_id`` and ``experiments.mlflow_run_id`` — MLflow
  experiment tracking was removed; these columns were left NULL.

The ``model_kind`` enum is shared by ``model_artifacts``/``experiments`` and is
intentionally NOT dropped. ``downgrade`` recreates the table + columns exactly as
the baseline defined them (referencing the existing ``model_kind`` enum without
re-creating it).

Hand-rolled. Mirrors ``0001_baseline.py``.

Revision ID: 0004_drop_traffic_mlflow
Revises: 0003_batch_source_mobile
Create Date: 2026-06-30 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_drop_traffic_mlflow"
down_revision = "0003_batch_source_mobile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # drop_table cascades the table's indexes, FKs and check constraint.
    op.drop_table("traffic_splits")
    op.drop_column("experiments", "mlflow_run_id")
    op.drop_column("model_artifacts", "mlflow_run_id")


def downgrade() -> None:
    op.add_column(
        "model_artifacts",
        sa.Column("mlflow_run_id", sa.String(64), nullable=True),
    )
    op.add_column(
        "experiments",
        sa.Column("mlflow_run_id", sa.String(64), nullable=True),
    )

    # Reference the existing enum without re-creating it.
    model_kind = postgresql.ENUM(
        "detection", "classification", name="model_kind", create_type=False
    )

    op.create_table(
        "traffic_splits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", model_kind, nullable=False),
        sa.Column(
            "seed_type_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("seed_types.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "model_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("model_artifacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("weight", sa.SmallInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("weight >= 0 AND weight <= 100", name="ck_traffic_splits_weight_range"),
    )
    op.create_index("ix_traffic_splits_kind_seed_type_id", "traffic_splits", ["kind", "seed_type_id"])
    op.create_index("ix_traffic_splits_model_id", "traffic_splits", ["model_id"])
    op.create_index("ix_traffic_splits_is_active", "traffic_splits", ["is_active"])
