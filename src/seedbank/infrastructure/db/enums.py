"""Database enumerations.

Each Python `StrEnum` maps to a real Postgres ENUM type via
`sqlalchemy.Enum(..., native_enum=True, name="<pg_type_name>")`.

Native ENUMs give us:
- type-safe inserts (no typo'd status strings)
- compact storage (4 bytes vs varchar)
- pg_dump round-trips cleanly

The trade-off is that adding a value requires `ALTER TYPE ... ADD VALUE`,
which is what the data-migration discipline in `db-architect.md` is for.
"""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy import Enum as SAEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    AI_DEVELOPER = "ai_developer"
    END_USER = "end_user"


class BatchStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIAL = "partial"


class BatchSource(StrEnum):
    API = "api"
    WEB = "web"
    SDK = "sdk"


class LocationSource(StrEnum):
    DEVICE_GPS = "device_gps"
    MANUAL = "manual"
    EXIF = "exif"
    NONE = "none"


class ModelKind(StrEnum):
    DETECTION = "detection"
    CLASSIFICATION = "classification"


class ModelBackend(StrEnum):
    TORCH_LOCAL = "torch_local"
    ROBOFLOW = "roboflow"
    YOLO = "yolo"


class ModelStatus(StrEnum):
    REGISTERED = "registered"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


class SeedQuality(StrEnum):
    GOOD = "good"
    BAD = "bad"


class ExperimentStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


# ── Reusable Postgres ENUM type factories ────────────────────────────────────
# `create_type=False` is set on column-level usage in models so the type is
# only emitted once (via the standalone Enum constructions below registered
# on Base.metadata via direct CREATE in the migration).

USER_ROLE_ENUM = SAEnum(
    UserRole,
    name="user_role",
    native_enum=True,
    values_callable=lambda e: [m.value for m in e],
    validate_strings=True,
)

BATCH_STATUS_ENUM = SAEnum(
    BatchStatus,
    name="batch_status",
    native_enum=True,
    values_callable=lambda e: [m.value for m in e],
    validate_strings=True,
)

BATCH_SOURCE_ENUM = SAEnum(
    BatchSource,
    name="batch_source",
    native_enum=True,
    values_callable=lambda e: [m.value for m in e],
    validate_strings=True,
)

LOCATION_SOURCE_ENUM = SAEnum(
    LocationSource,
    name="location_source",
    native_enum=True,
    values_callable=lambda e: [m.value for m in e],
    validate_strings=True,
)

MODEL_KIND_ENUM = SAEnum(
    ModelKind,
    name="model_kind",
    native_enum=True,
    values_callable=lambda e: [m.value for m in e],
    validate_strings=True,
)

MODEL_BACKEND_ENUM = SAEnum(
    ModelBackend,
    name="model_backend",
    native_enum=True,
    values_callable=lambda e: [m.value for m in e],
    validate_strings=True,
)

MODEL_STATUS_ENUM = SAEnum(
    ModelStatus,
    name="model_status",
    native_enum=True,
    values_callable=lambda e: [m.value for m in e],
    validate_strings=True,
)

SEED_QUALITY_ENUM = SAEnum(
    SeedQuality,
    name="seed_quality",
    native_enum=True,
    values_callable=lambda e: [m.value for m in e],
    validate_strings=True,
)

EXPERIMENT_STATUS_ENUM = SAEnum(
    ExperimentStatus,
    name="experiment_status",
    native_enum=True,
    values_callable=lambda e: [m.value for m in e],
    validate_strings=True,
)


__all__ = [
    "BATCH_SOURCE_ENUM",
    "BATCH_STATUS_ENUM",
    "EXPERIMENT_STATUS_ENUM",
    "LOCATION_SOURCE_ENUM",
    "MODEL_BACKEND_ENUM",
    "MODEL_KIND_ENUM",
    "MODEL_STATUS_ENUM",
    "SEED_QUALITY_ENUM",
    "USER_ROLE_ENUM",
    "BatchSource",
    "BatchStatus",
    "ExperimentStatus",
    "LocationSource",
    "ModelBackend",
    "ModelKind",
    "ModelStatus",
    "SeedQuality",
    "UserRole",
]
