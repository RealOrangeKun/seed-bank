"""SQLAlchemy 2.0 ORM models — the OLTP schema.

This is the source of truth for the Postgres schema. Alembic autogenerate
diffs against `Base.metadata` to produce migrations.

Hard rules enforced here (see `.claude/agents/db-architect.md`):
- UUIDv7 PKs everywhere via `core.ids.uuid7`.
- Every FK has an explicit `Index(...)` (autogenerate skips them).
- Every "type" / "status" column is a Postgres ENUM (see `enums.py`).
- Confidence + percentages are `Numeric(5, 4)`. Bbox coords are `Numeric(7, 6)`.
- All timestamps are `TIMESTAMP WITH TIME ZONE`.

NOTE on the user-must-have-password-or-oauth invariant: a true CHECK
constraint would need to peek at `oauth_accounts`, which Postgres CHECK
constraints can't do. The invariant is enforced in
`services/auth_service.py` (Phase 4) on user creation/update paths.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, INET, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from seedbank.core.ids import uuid7

from .base import Base, SoftDeleteMixin, TimestampMixin
from .enums import (
    BATCH_SOURCE_ENUM,
    BATCH_STATUS_ENUM,
    EXPERIMENT_STATUS_ENUM,
    LOCATION_SOURCE_ENUM,
    MODEL_BACKEND_ENUM,
    MODEL_KIND_ENUM,
    MODEL_STATUS_ENUM,
    SEED_QUALITY_ENUM,
    USER_ROLE_ENUM,
)


# ── Identity & access ───────────────────────────────────────────────────────


class User(Base, TimestampMixin, SoftDeleteMixin):
    """Application user.

    `hashed_password` is nullable so OAuth-only users are allowed; service-layer
    code MUST ensure a user has either a password or at least one
    `oauth_accounts` row (cross-table invariant — see module docstring).
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    email: Mapped[str] = mapped_column(CITEXT(), nullable=False, unique=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(
        USER_ROLE_ENUM,
        nullable=False,
        server_default=text("'end_user'"),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    oauth_accounts: Mapped[list[OAuthAccount]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    api_keys: Mapped[list[ApiKey]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_users_role", "role"),
        Index("ix_users_is_active", "is_active"),
    )


class OAuthAccount(Base, TimestampMixin):
    __tablename__ = "oauth_accounts"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="oauth_accounts")

    __table_args__ = (
        UniqueConstraint("provider", "provider_subject", name="uq_oauth_provider_subject"),
        CheckConstraint(
            "provider IN ('google', 'github')",
            name="provider_supported",
        ),
        Index("ix_oauth_accounts_user_id", "user_id"),
    )


class RefreshToken(Base, TimestampMixin):
    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ip: Mapped[str | None] = mapped_column(INET, nullable=True)

    user: Mapped[User] = relationship(back_populates="refresh_tokens")

    __table_args__ = (
        Index("ix_refresh_tokens_user_id", "user_id"),
        Index("ix_refresh_tokens_replaced_by_id", "replaced_by_id"),
        Index("ix_refresh_tokens_expires_at", "expires_at"),
        # Partial unique on live tokens: detects replay attempts on a still-valid token.
        Index(
            "uq_refresh_tokens_live_hash",
            "token_hash",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )


class ApiKey(Base, TimestampMixin):
    __tablename__ = "api_keys"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(
        ARRAY(String(64)), nullable=False, server_default=text("'{}'::varchar[]")
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="api_keys")

    __table_args__ = (
        Index("ix_api_keys_user_id", "user_id"),
        Index("ix_api_keys_prefix", "prefix"),
    )


class AuditLog(Base):
    """Append-only audit trail. Hard delete is forbidden — log retention is
    a housekeeping job, not a deletion path."""

    __tablename__ = "audit_log"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    actor_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    audit_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_audit_log_actor_id", "actor_id"),
        Index("ix_audit_log_action", "action"),
        Index("ix_audit_log_target_type_target_id", "target_type", "target_id"),
        Index("ix_audit_log_occurred_at", "occurred_at"),
    )


# ── Catalog & ML registry ───────────────────────────────────────────────────


class SeedType(Base, TimestampMixin):
    __tablename__ = "seed_types"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_confidence_threshold: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        server_default=text("0.5000"),
    )

    __table_args__ = (
        CheckConstraint(
            "default_confidence_threshold >= 0 AND default_confidence_threshold <= 1",
            name="default_confidence_threshold_range",
        ),
    )


class Supplier(Base, TimestampMixin, SoftDeleteMixin):
    """Suppliers of seeds.

    Two kinds:
      - global (`is_global=true`, `created_by_user_id IS NULL`) — admin-curated,
        visible to everyone.
      - private (`is_global=false`, `created_by_user_id IS NOT NULL`) — owned by
        a single user.

    Partial uniques keep names distinct within their visibility scope.
    """

    __tablename__ = "suppliers"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(CITEXT(), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    is_global: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    supplier_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "(is_global AND created_by_user_id IS NULL) "
            "OR (NOT is_global AND created_by_user_id IS NOT NULL)",
            name="global_xor_owner",
        ),
        Index(
            "uq_suppliers_global_lower_name",
            func.lower(name),
            unique=True,
            postgresql_where=text("is_global"),
        ),
        Index(
            "uq_suppliers_private_owner_lower_name",
            "created_by_user_id",
            func.lower(name),
            unique=True,
            postgresql_where=text("NOT is_global"),
        ),
        Index("ix_suppliers_is_global_is_active", "is_global", "is_active"),
        Index("ix_suppliers_created_by_user_id", "created_by_user_id"),
    )


class ModelArtifact(Base, TimestampMixin):
    __tablename__ = "model_artifacts"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    kind: Mapped[str] = mapped_column(MODEL_KIND_ENUM, nullable=False)
    backend: Mapped[str] = mapped_column(MODEL_BACKEND_ENUM, nullable=False)
    seed_type_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("seed_types.id", ondelete="RESTRICT"),
        nullable=True,
    )
    artifact_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    training_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    mlflow_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        MODEL_STATUS_ENUM, nullable=False, server_default=text("'registered'")
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_model_artifacts_name_version"),
        # At most one production model per (kind, seed_type_id).
        Index(
            "uq_model_artifacts_one_prod_per_kind_seed",
            "kind",
            "seed_type_id",
            unique=True,
            postgresql_where=text("status = 'production'"),
        ),
        Index("ix_model_artifacts_seed_type_id", "seed_type_id"),
        Index("ix_model_artifacts_created_by", "created_by"),
        Index("ix_model_artifacts_status", "status"),
        Index("ix_model_artifacts_kind", "kind"),
    )


class ModelMetric(Base):
    __tablename__ = "model_metrics"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    model_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("model_artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    dataset_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="SET NULL"),
        nullable=True,
    )
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    metric_value: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_model_metrics_model_id_metric_name", "model_id", "metric_name"),
        Index("ix_model_metrics_dataset_id", "dataset_id"),
    )


class Dataset(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "datasets"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (Index("ix_datasets_created_by", "created_by"),)

    items: Mapped[list[DatasetItem]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
    )


class DatasetItem(Base):
    __tablename__ = "dataset_items"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    dataset_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    image_storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    ground_truth: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)

    __table_args__ = (
        Index("ix_dataset_items_dataset_id", "dataset_id"),
        UniqueConstraint(
            "dataset_id",
            "image_storage_key",
            name="uq_dataset_items_dataset_storage_key",
        ),
    )

    dataset: Mapped[Dataset] = relationship(back_populates="items")


class TrafficSplit(Base, TimestampMixin):
    __tablename__ = "traffic_splits"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    kind: Mapped[str] = mapped_column(MODEL_KIND_ENUM, nullable=False)
    seed_type_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("seed_types.id", ondelete="CASCADE"),
        nullable=True,
    )
    model_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("model_artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    weight: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("weight >= 0 AND weight <= 100", name="weight_range"),
        Index("ix_traffic_splits_kind_seed_type_id", "kind", "seed_type_id"),
        Index("ix_traffic_splits_model_id", "model_id"),
        Index("ix_traffic_splits_is_active", "is_active"),
    )


# ── Experiments ─────────────────────────────────────────────────────────────


class Experiment(Base, TimestampMixin):
    __tablename__ = "experiments"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(
        EXPERIMENT_STATUS_ENUM, nullable=False, server_default=text("'pending'")
    )
    model_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("model_artifacts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    dataset_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    summary_metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    mlflow_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_experiments_model_id", "model_id"),
        Index("ix_experiments_dataset_id", "dataset_id"),
        Index("ix_experiments_created_by", "created_by"),
        Index("ix_experiments_status", "status"),
    )

    results: Mapped[list[ExperimentResult]] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
    )


class ExperimentResult(Base):
    __tablename__ = "experiment_results"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    experiment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
    )
    dataset_item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("dataset_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    predicted_boxes: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_experiment_results_experiment_id", "experiment_id"),
        Index("ix_experiment_results_dataset_item_id", "dataset_item_id"),
    )

    experiment: Mapped[Experiment] = relationship(back_populates="results")


# ── Inference data ──────────────────────────────────────────────────────────


class ScanBatch(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "scan_batches"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    supplier_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        BATCH_STATUS_ENUM, nullable=False, server_default=text("'pending'")
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(
        BATCH_SOURCE_ENUM, nullable=False, server_default=text("'api'")
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Capture geo — all nullable; populated only when the client supplied it.
    location_source: Mapped[str | None] = mapped_column(LOCATION_SOURCE_ENUM, nullable=True)
    gps_lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    gps_long: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    geo_city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    geo_country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)

    images: Mapped[list[ScanImage]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # Both lat/long present, or both NULL — never half a coordinate.
        CheckConstraint(
            "(gps_lat IS NULL) = (gps_long IS NULL)",
            name="gps_lat_long_paired",
        ),
        CheckConstraint(
            "gps_lat IS NULL OR (gps_lat >= -90 AND gps_lat <= 90)",
            name="gps_lat_range",
        ),
        CheckConstraint(
            "gps_long IS NULL OR (gps_long >= -180 AND gps_long <= 180)",
            name="gps_long_range",
        ),
        CheckConstraint(
            "geo_country_code IS NULL OR geo_country_code ~ '^[A-Z]{2}$'",
            name="geo_country_code_iso2",
        ),
        Index("ix_scan_batches_user_id_submitted_at", "user_id", "submitted_at"),
        Index(
            "ix_scan_batches_supplier_id",
            "supplier_id",
            postgresql_where=text("supplier_id IS NOT NULL"),
        ),
        Index("ix_scan_batches_status", "status"),
        Index("ix_scan_batches_geo_country_code", "geo_country_code"),
    )


class ScanImage(Base):
    __tablename__ = "scan_images"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    batch_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("scan_batches.id", ondelete="CASCADE"),
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    batch: Mapped[ScanBatch] = relationship(back_populates="images")
    inferences: Mapped[list[Inference]] = relationship(
        back_populates="image",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_scan_images_batch_id", "batch_id"),
        Index("ix_scan_images_sha256", "sha256"),
        UniqueConstraint("batch_id", "storage_key", name="uq_scan_images_batch_storage_key"),
        CheckConstraint("size_bytes > 0", name="size_bytes_positive"),
    )


class Inference(Base):
    """One row per (image, model) inference attempt.

    `model_id` is NOT NULL — every inference is traceable to the exact model
    artifact that produced it. This is the join column for A/B analyses.
    """

    __tablename__ = "inferences"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    image_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("scan_images.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("model_artifacts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    backend: Mapped[str] = mapped_column(MODEL_BACKEND_ENUM, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    image: Mapped[ScanImage] = relationship(back_populates="inferences")
    detections: Mapped[list[SeedDetection]] = relationship(
        back_populates="inference",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_inferences_image_id", "image_id"),
        Index("ix_inferences_model_id", "model_id"),
        Index("ix_inferences_occurred_at", "occurred_at"),
        UniqueConstraint("image_id", "model_id", name="uq_inferences_image_model"),
    )


class SeedDetection(Base):
    """One detected / classified seed within an `inferences` row."""

    __tablename__ = "seed_detections"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    inference_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("inferences.id", ondelete="CASCADE"),
        nullable=False,
    )
    seed_type_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("seed_types.id", ondelete="RESTRICT"),
        nullable=True,
    )
    quality: Mapped[str | None] = mapped_column(SEED_QUALITY_ENUM, nullable=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    detection_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    box_x_norm: Mapped[Decimal] = mapped_column(Numeric(7, 6), nullable=False)
    box_y_norm: Mapped[Decimal] = mapped_column(Numeric(7, 6), nullable=False)
    box_w_norm: Mapped[Decimal] = mapped_column(Numeric(7, 6), nullable=False)
    box_h_norm: Mapped[Decimal] = mapped_column(Numeric(7, 6), nullable=False)
    area_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
    aspect_ratio: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)

    inference: Mapped[Inference] = relationship(back_populates="detections")

    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        CheckConstraint(
            "detection_confidence IS NULL OR "
            "(detection_confidence >= 0 AND detection_confidence <= 1)",
            name="detection_confidence_range",
        ),
        CheckConstraint(
            "box_x_norm >= 0 AND box_x_norm <= 1 "
            "AND box_y_norm >= 0 AND box_y_norm <= 1 "
            "AND box_w_norm > 0 AND box_w_norm <= 1 "
            "AND box_h_norm > 0 AND box_h_norm <= 1",
            name="bbox_normalized",
        ),
        Index("ix_seed_detections_inference_id", "inference_id"),
        Index("ix_seed_detections_seed_type_quality", "seed_type_id", "quality"),
    )


__all__ = [
    "ApiKey",
    "AuditLog",
    "Dataset",
    "DatasetItem",
    "Experiment",
    "ExperimentResult",
    "Inference",
    "ModelArtifact",
    "ModelMetric",
    "OAuthAccount",
    "RefreshToken",
    "ScanBatch",
    "ScanImage",
    "SeedDetection",
    "SeedType",
    "Supplier",
    "TrafficSplit",
    "User",
]
