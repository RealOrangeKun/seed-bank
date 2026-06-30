"""Request (``*In``) schemas reject unknown keys.

ADR 0001 (P3): dataset/experiment inputs used to silently drop typo'd fields
(``descrption=...`` was accepted and ignored). They now share
``STRICT_INPUT = ConfigDict(extra="forbid")`` so a typo surfaces as a 422
instead of being swallowed.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from seedbank.schemas.dataset import (
    DatasetCreateIn,
    DatasetItemCreateIn,
    DatasetItemsBulkIn,
)
from seedbank.schemas.experiment import ExperimentCreateIn


def test_dataset_create_rejects_unknown_field() -> None:
    DatasetCreateIn(name="set")  # valid baseline
    with pytest.raises(ValidationError):
        DatasetCreateIn(name="set", descrption="typo")


def test_dataset_item_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        DatasetItemCreateIn(image_storage_key="k", labl="typo")


def test_dataset_bulk_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        DatasetItemsBulkIn(
            items=[DatasetItemCreateIn(image_storage_key="k")],
            extra=1,
        )


def test_experiment_create_rejects_unknown_field_but_keeps_model_prefix() -> None:
    # ``model_id`` must still be accepted (protected-namespace opt-out survives).
    ExperimentCreateIn(name="x", model_id=uuid4(), dataset_id=uuid4())
    with pytest.raises(ValidationError):
        ExperimentCreateIn(name="x", model_id=uuid4(), dataset_id=uuid4(), typo=1)
