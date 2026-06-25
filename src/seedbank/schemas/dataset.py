"""Pydantic shapes for ``/api/v1/datasets``.

Datasets are immutable from an experiment's point of view: appending an
item to a dataset never changes the rows already linked to past
experiments (each ``ExperimentResult`` keeps ``dataset_item_id``). For
that reason the API has no item-level update or delete; you append, you
list, and you may soft-delete the whole dataset.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from seedbank.schemas.common import STRICT_INPUT

# Cap the bulk-add payload — the underlying transaction grows with item
# count, and lists this large should come from ``scripts/upload_dataset.py``
# anyway.
_MAX_ITEMS_PER_BULK = 1000


class DatasetCreateIn(BaseModel):
    """Request body for ``POST /datasets``."""

    model_config = STRICT_INPUT

    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)


class DatasetItemCreateIn(BaseModel):
    """One item inside a bulk-add request.

    ``image_storage_key`` references an object the caller has already
    uploaded to MinIO ``seedbank-datasets`` (presigned PUT or
    ``scripts/upload_dataset.py``). The server does not fetch or
    validate the bytes synchronously — the experiment runner does that
    when it dereferences the item.

    ``ground_truth`` is a free-form JSON document; the experiment runner
    enforces the schema (``{"kind": "detection", "boxes": [...]}`` or
    ``{"kind": "classification", "label": "good"}``).
    """

    model_config = STRICT_INPUT

    image_storage_key: str = Field(min_length=1, max_length=512)
    ground_truth: dict[str, Any] | None = None
    checksum: str | None = Field(default=None, max_length=128)


class DatasetItemsBulkIn(BaseModel):
    """Request body for ``POST /datasets/{id}/items``."""

    model_config = STRICT_INPUT

    items: list[DatasetItemCreateIn] = Field(min_length=1, max_length=_MAX_ITEMS_PER_BULK)


class DatasetOut(BaseModel):
    """List + detail response for a :class:`Dataset`."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    item_count: int = 0


class DatasetItemOut(BaseModel):
    """Listing entry for a :class:`DatasetItem`."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    image_storage_key: str
    ground_truth: dict[str, Any] | None = None
    checksum: str | None = None


class DatasetItemsAddedOut(BaseModel):
    """Response body for the bulk-add endpoint."""

    added: int


__all__ = [
    "DatasetCreateIn",
    "DatasetItemCreateIn",
    "DatasetItemOut",
    "DatasetItemsAddedOut",
    "DatasetItemsBulkIn",
    "DatasetOut",
]
