"""Pydantic v2 DTOs for the unified ``/analyze`` + ``/batches`` endpoints.

Boundary rules (CLAUDE.md):

- Domain entities never cross the wire — these schemas wrap every ORM row
  read or every multipart form chunk written.
- ``confidence`` and bbox columns are ``Decimal`` (the DB stores
  ``NUMERIC(5,4)`` / ``NUMERIC(7,6)``). Pydantic v2 emits decimal strings
  rather than lossy floats, so clients see ``"0.9234"`` and not
  ``0.9233999999...``.
- Every response schema sets ``from_attributes=True`` so a service can do
  ``BatchOut.model_validate(orm_row)`` without round-tripping through dicts.
- ``model_id`` is a legitimate field on the analyze form and on the
  inference response. Pydantic v2 reserves ``model_*`` for its own use,
  so the affected schemas explicitly opt out via ``protected_namespaces=()``.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from seedbank.infrastructure.db.enums import (
    BatchSource,
    BatchStatus,
    LocationSource,
    ModelBackend,
    SeedQuality,
)


class AnalyzeQueryIn(BaseModel):
    """Multipart form fields the router reads alongside ``files``.

    The uploaded files themselves are bound separately via
    ``UploadFile`` parameters in the router; this schema only models the
    optional metadata so we get one place to add validation (regex on
    ``country_code``, decimal precision, etc.).
    """

    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    supplier_id: UUID | None = None
    seed_type_id: UUID | None = None
    model_id: UUID | None = None
    gps_lat: Annotated[Decimal | None, Field(default=None, max_digits=9, decimal_places=6)] = None
    gps_long: Annotated[Decimal | None, Field(default=None, max_digits=9, decimal_places=6)] = None
    country_code: Annotated[
        str | None,
        Field(default=None, min_length=2, max_length=2, pattern="^[A-Z]{2}$"),
    ] = None


class SeedDetectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    seed_type_id: UUID | None = None
    quality: SeedQuality | None = None
    confidence: Decimal
    detection_confidence: Decimal | None = None
    box_x_norm: Decimal
    box_y_norm: Decimal
    box_w_norm: Decimal
    box_h_norm: Decimal
    area_px: int | None = None
    width_px: int | None = None
    height_px: int | None = None
    aspect_ratio: Decimal | None = None


class InferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID
    # The audit anchor — pillar 5 of CLAUDE.md. Every detection joins
    # back to the exact ``model_artifacts`` row that produced it.
    model_id: UUID
    backend: ModelBackend
    latency_ms: int | None = None
    error: str | None = None
    occurred_at: datetime
    detections: list[SeedDetectionOut] = Field(default_factory=list)


class ScanImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    storage_key: str
    content_type: str
    size_bytes: int
    sha256: str
    width: int | None = None
    height: int | None = None
    uploaded_at: datetime
    inferences: list[InferenceOut] = Field(default_factory=list)


class BatchOut(BaseModel):
    """Lightweight batch summary — the ``POST /analyze`` response and
    each row of the ``GET /batches`` page.

    ``image_count`` is populated by the service layer (a count query or
    ``len(files)``); it is *not* a column on ``scan_batches``.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    status: BatchStatus
    source: BatchSource
    submitted_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    supplier_id: UUID | None = None
    image_count: int = 0


class BatchDetailOut(BatchOut):
    """Full nested envelope for ``GET /batches/{id}`` — batch → images
    → inferences → detections, eager-loaded by the repository."""

    error_message: str | None = None
    location_source: LocationSource | None = None
    gps_lat: Decimal | None = None
    gps_long: Decimal | None = None
    geo_city: str | None = None
    geo_country_code: str | None = None
    images: list[ScanImageOut] = Field(default_factory=list)


class ImageUrlOut(BaseModel):
    """A short-lived, browser-reachable URL for one stored scan image.

    Returned by ``GET /batches/{id}/image-urls`` so the client can render the
    original image (and overlay normalized bounding boxes) without the bytes
    ever traversing the API process. ``expires_at`` lets the client refetch
    before the presigned URL lapses.
    """

    image_id: UUID
    url: str
    expires_at: datetime


class BatchBulkDeleteIn(BaseModel):
    """Request body for ``POST /batches/delete`` — bulk soft-delete.

    Capped so a single call can't fan out an unbounded ``IN (...)``. IDs the
    caller doesn't own (or that are already deleted) are silently skipped; the
    response reports how many actually took effect.
    """

    model_config = ConfigDict(extra="forbid")

    batch_ids: Annotated[list[UUID], Field(min_length=1, max_length=200)]


class BatchDeleteResult(BaseModel):
    """How many batches a (bulk) delete actually soft-deleted."""

    deleted: int


__all__ = [
    "AnalyzeQueryIn",
    "BatchBulkDeleteIn",
    "BatchDeleteResult",
    "BatchDetailOut",
    "BatchOut",
    "ImageUrlOut",
    "InferenceOut",
    "ScanImageOut",
    "SeedDetectionOut",
]
