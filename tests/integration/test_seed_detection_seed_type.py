"""Integration: ``SeedDetection.seed_type`` resolves the catalog label.

ADR 0001 (P3): batch-detail responses showed "Seed type –" because a
detection only carried a raw ``seed_type_id``. The eager ``seed_type``
relationship now lets the detail repository load the catalog row and
``SeedDetectionOut`` embed the human label. Runs against a real Postgres
testcontainer so the ``selectin`` eager-load is exercised end to end.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from seedbank.infrastructure.db.enums import (
    ModelBackend,
    ModelKind,
    ModelStatus,
    UserRole,
)
from seedbank.infrastructure.db.models import (
    Inference,
    ModelArtifact,
    ScanBatch,
    ScanImage,
    SeedDetection,
    SeedType,
    User,
)
from seedbank.infrastructure.db.repositories import ScanBatchRepository
from seedbank.schemas.analysis import SeedDetectionOut

pytestmark = pytest.mark.integration


async def test_detection_resolves_seed_type_label(db_session: AsyncSession) -> None:
    user = User(
        email="label@example.com",
        hashed_password="bcrypt$irrelevant",
        role=UserRole.END_USER.value,
    )
    seed_type = SeedType(code="coffee", display_name="Coffee")
    model = ModelArtifact(
        name="detector",
        version="v1",
        kind=ModelKind.DETECTION.value,
        backend=ModelBackend.TORCH_LOCAL.value,
        artifact_uri="s3://models/detector/v1/weights.pth",
        status=ModelStatus.PRODUCTION.value,
    )
    db_session.add_all([user, seed_type, model])
    await db_session.flush()

    batch = ScanBatch(user_id=user.id, status="succeeded", source="api")
    db_session.add(batch)
    await db_session.flush()

    image = ScanImage(
        batch_id=batch.id,
        storage_key="a.jpg",
        content_type="image/jpeg",
        size_bytes=1,
        sha256="0" * 64,
        width=100,
        height=100,
    )
    db_session.add(image)
    await db_session.flush()

    inference = Inference(
        image_id=image.id,
        model_id=model.id,
        backend=ModelBackend.TORCH_LOCAL.value,
    )
    db_session.add(inference)
    await db_session.flush()

    detection = SeedDetection(
        inference_id=inference.id,
        seed_type_id=seed_type.id,
        quality="good",
        confidence=Decimal("0.9000"),
        box_x_norm=Decimal("0.100000"),
        box_y_norm=Decimal("0.100000"),
        box_w_norm=Decimal("0.200000"),
        box_h_norm=Decimal("0.200000"),
    )
    db_session.add(detection)
    await db_session.commit()
    # Drop the identity map so the repository builds fresh instances and the
    # ``selectin`` eager-load really fires (mimics a cold request session).
    db_session.expunge_all()

    repo = ScanBatchRepository(db_session)
    loaded = await repo.get_with_images_and_detections(batch.id, user.id)

    assert loaded is not None
    [img] = loaded.images
    [inf] = img.inferences
    [det] = inf.detections

    # Relationship resolves without a separate query/lazy load.
    assert det.seed_type is not None
    assert det.seed_type.code == "coffee"
    assert det.seed_type.display_name == "Coffee"

    # And the response schema embeds the label.
    out = SeedDetectionOut.model_validate(det)
    assert out.seed_type_id == seed_type.id
    assert out.seed_type is not None
    assert out.seed_type.code == "coffee"
    assert out.seed_type.display_name == "Coffee"


async def test_detection_without_seed_type_is_none(db_session: AsyncSession) -> None:
    """An untyped detection (detector couldn't attribute a class) serializes
    with ``seed_type=None`` rather than blowing up the eager load."""
    user = User(
        email="notype@example.com",
        hashed_password="bcrypt$irrelevant",
        role=UserRole.END_USER.value,
    )
    model = ModelArtifact(
        name="detector2",
        version="v1",
        kind=ModelKind.DETECTION.value,
        backend=ModelBackend.TORCH_LOCAL.value,
        artifact_uri="s3://models/detector2/v1/weights.pth",
        status=ModelStatus.PRODUCTION.value,
    )
    db_session.add_all([user, model])
    await db_session.flush()
    batch = ScanBatch(user_id=user.id, status="succeeded", source="api")
    db_session.add(batch)
    await db_session.flush()
    image = ScanImage(
        batch_id=batch.id,
        storage_key="b.jpg",
        content_type="image/jpeg",
        size_bytes=1,
        sha256="0" * 64,
        width=100,
        height=100,
    )
    db_session.add(image)
    await db_session.flush()
    inference = Inference(
        image_id=image.id,
        model_id=model.id,
        backend=ModelBackend.TORCH_LOCAL.value,
    )
    db_session.add(inference)
    await db_session.flush()
    detection = SeedDetection(
        inference_id=inference.id,
        seed_type_id=None,
        confidence=Decimal("0.5000"),
        box_x_norm=Decimal("0.100000"),
        box_y_norm=Decimal("0.100000"),
        box_w_norm=Decimal("0.200000"),
        box_h_norm=Decimal("0.200000"),
    )
    db_session.add(detection)
    await db_session.commit()
    db_session.expunge_all()

    repo = ScanBatchRepository(db_session)
    loaded = await repo.get_with_images_and_detections(batch.id, user.id)
    assert loaded is not None
    [det] = loaded.images[0].inferences[0].detections
    assert det.seed_type is None
    out = SeedDetectionOut.model_validate(det)
    assert out.seed_type is None
