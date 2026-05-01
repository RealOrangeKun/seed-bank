"""Integration tests for the OLTP→ClickHouse dual-write path (Phase 8).

These exercise the worker task bodies directly (no Celery broker, no
``asyncio.run`` wrapper) against a real Postgres testcontainer **and** a
real ClickHouse testcontainer. The unit tier already pins serialization
shape; this tier pins the wire contract: rows seeded in OLTP land in CH
with the right columns, types, and dim joins resolvable.

Why bypass Celery: the Celery wrapper is a 3-line ``asyncio.run`` shim
that exists only because Celery's worker contract is sync. Driving the
async core directly is faster, deterministic, and the failure mode
(broker miswiring) is covered by the unit tier in
``test_dwh_helpers.py``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest

from seedbank.infrastructure.db.enums import UserRole
from seedbank.infrastructure.db.models import (
    Inference,
    ModelArtifact,
    ScanBatch,
    ScanImage,
    SeedDetection,
    SeedType,
    User,
)
from seedbank.workers.tasks.dwh import (
    _async_sync_detections,
    _async_sync_inference,
    _async_sync_scan_batch,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


# ── Seed helpers (kept inline; per-test data shape is small) ───────────────


async def _seed_user(session: AsyncSession, *, email: str = "dwh@e.com") -> User:
    u = User(
        email=email,
        hashed_password="bcrypt$irrelevant",
        role=UserRole.AI_DEVELOPER.value,
        is_active=True,
        is_verified=True,
    )
    session.add(u)
    await session.flush()
    return u


async def _seed_seed_type(session: AsyncSession, *, code: str = "coffee") -> SeedType:
    st = SeedType(
        code=code,
        display_name=code.title(),
        default_confidence_threshold=Decimal("0.5000"),
    )
    session.add(st)
    await session.flush()
    return st


async def _seed_model(
    session: AsyncSession,
    *,
    seed_type_id: UUID | None,
    kind: str = "detection",
    name: str = "yolo-detect",
    version: str = "v1",
) -> ModelArtifact:
    m = ModelArtifact(
        name=name,
        version=version,
        kind=kind,
        backend="torch_local",
        seed_type_id=seed_type_id,
        artifact_uri="s3://test/dummy.pth",
        status="production",
    )
    session.add(m)
    await session.flush()
    return m


async def _seed_batch(session: AsyncSession, *, user_id: UUID) -> ScanBatch:
    b = ScanBatch(
        user_id=user_id,
        status="pending",
        source="api",
        geo_country_code="EG",
    )
    session.add(b)
    await session.flush()
    return b


async def _seed_image(session: AsyncSession, *, batch_id: UUID) -> ScanImage:
    img = ScanImage(
        batch_id=batch_id,
        storage_key=f"img/{batch_id}/x.jpg",
        content_type="image/jpeg",
        size_bytes=1024,
        sha256="0" * 64,
        width=640,
        height=480,
    )
    session.add(img)
    await session.flush()
    return img


async def _seed_inference(session: AsyncSession, *, image_id: UUID, model_id: UUID) -> Inference:
    inf = Inference(
        image_id=image_id,
        model_id=model_id,
        backend="torch_local",
        latency_ms=42,
        occurred_at=datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC),
    )
    session.add(inf)
    await session.flush()
    return inf


async def _seed_detection(
    session: AsyncSession,
    *,
    inference_id: UUID,
    seed_type_id: UUID | None,
    quality: str | None = "good",
    confidence: Decimal = Decimal("0.9123"),
) -> SeedDetection:
    d = SeedDetection(
        inference_id=inference_id,
        seed_type_id=seed_type_id,
        quality=quality,
        confidence=confidence,
        detection_confidence=Decimal("0.9876"),
        box_x_norm=Decimal("0.100000"),
        box_y_norm=Decimal("0.200000"),
        box_w_norm=Decimal("0.300000"),
        box_h_norm=Decimal("0.400000"),
        width_px=192,
        height_px=192,
        area_px=36864,
        aspect_ratio=Decimal("1.0000"),
    )
    session.add(d)
    await session.flush()
    return d


# ── fact_inference round-trip ──────────────────────────────────────────────


@pytest.mark.usefixtures("_truncate_clickhouse")
async def test_sync_inference_writes_fact_row_and_dims(
    db_session: AsyncSession,
    clickhouse_client: Any,
) -> None:
    """A finished Inference becomes one fact_inference row with all dim
    FKs resolvable in dim_user / dim_model / dim_seed_type."""
    user = await _seed_user(db_session)
    st = await _seed_seed_type(db_session)
    model = await _seed_model(db_session, seed_type_id=st.id)
    batch = await _seed_batch(db_session, user_id=user.id)
    img = await _seed_image(db_session, batch_id=batch.id)
    inf = await _seed_inference(db_session, image_id=img.id, model_id=model.id)
    await db_session.commit()

    await _async_sync_inference(inf.id)

    rows = await clickhouse_client.query(
        "SELECT inference_id, image_id, batch_id, user_id, model_id, "
        "seed_type_id, backend, model_kind, latency_ms, has_error "
        "FROM fact_inference FINAL WHERE inference_id = %(id)s",
        {"id": str(inf.id)},
    )
    assert len(rows) == 1
    r = rows[0]
    assert UUID(str(r["inference_id"])) == inf.id
    assert UUID(str(r["image_id"])) == img.id
    assert UUID(str(r["batch_id"])) == batch.id
    assert UUID(str(r["user_id"])) == user.id
    assert UUID(str(r["model_id"])) == model.id
    assert UUID(str(r["seed_type_id"])) == st.id
    assert r["backend"] == "torch_local"
    assert r["model_kind"] == "detection"
    assert r["latency_ms"] == 42
    assert r["has_error"] in (0, False)

    # Dims joinable.
    dim_users = await clickhouse_client.query(
        "SELECT email FROM dim_user FINAL WHERE user_id = %(id)s",
        {"id": str(user.id)},
    )
    assert dim_users == [{"email": user.email}]

    dim_models = await clickhouse_client.query(
        "SELECT name, version, kind FROM dim_model FINAL WHERE model_id = %(id)s",
        {"id": str(model.id)},
    )
    assert dim_models == [{"name": model.name, "version": model.version, "kind": model.kind}]

    dim_st = await clickhouse_client.query(
        "SELECT code FROM dim_seed_type FINAL WHERE seed_type_id = %(id)s",
        {"id": str(st.id)},
    )
    assert dim_st == [{"code": st.code}]


# ── fact_detection round-trip ──────────────────────────────────────────────


@pytest.mark.usefixtures("_truncate_clickhouse")
async def test_sync_detections_writes_fact_rows_with_normalized_bbox(
    db_session: AsyncSession,
    clickhouse_client: Any,
) -> None:
    """Per-detection fan-out: each SeedDetection becomes one fact_detection
    row with confidence + bbox preserved as Decimal at full precision."""
    user = await _seed_user(db_session, email="det@e.com")
    st = await _seed_seed_type(db_session, code="rice")
    model = await _seed_model(db_session, seed_type_id=st.id, name="det", version="v2")
    batch = await _seed_batch(db_session, user_id=user.id)
    img = await _seed_image(db_session, batch_id=batch.id)
    inf = await _seed_inference(db_session, image_id=img.id, model_id=model.id)
    d1 = await _seed_detection(
        db_session,
        inference_id=inf.id,
        seed_type_id=st.id,
        quality="good",
    )
    d2 = await _seed_detection(
        db_session,
        inference_id=inf.id,
        seed_type_id=st.id,
        quality="bad",
        confidence=Decimal("0.5500"),
    )
    await db_session.commit()

    await _async_sync_detections(inf.id)

    rows = await clickhouse_client.query(
        "SELECT detection_id, quality, confidence, "
        "box_x_norm, box_y_norm, box_w_norm, box_h_norm "
        "FROM fact_detection FINAL WHERE inference_id = %(id)s "
        "ORDER BY confidence DESC",
        {"id": str(inf.id)},
    )
    assert len(rows) == 2
    ids = {UUID(str(r["detection_id"])) for r in rows}
    assert ids == {d1.id, d2.id}
    # Highest confidence row first per ORDER BY.
    assert rows[0]["quality"] == "good"
    assert rows[0]["confidence"] == Decimal("0.9123")
    # bbox preserved at NUMERIC(7,6) precision through driver round-trip.
    assert rows[0]["box_x_norm"] == Decimal("0.100000")
    assert rows[0]["box_w_norm"] == Decimal("0.300000")
    assert rows[1]["quality"] == "bad"
    assert rows[1]["confidence"] == Decimal("0.5500")


@pytest.mark.usefixtures("_truncate_clickhouse")
async def test_sync_detections_no_op_on_empty_inference(
    db_session: AsyncSession,
    clickhouse_client: Any,
) -> None:
    """An Inference with zero SeedDetections must not write any
    fact_detection rows. Guards the repo-level empty-rows short-circuit."""
    user = await _seed_user(db_session, email="empty@e.com")
    st = await _seed_seed_type(db_session, code="bean")
    model = await _seed_model(db_session, seed_type_id=st.id, name="empty", version="v1")
    batch = await _seed_batch(db_session, user_id=user.id)
    img = await _seed_image(db_session, batch_id=batch.id)
    inf = await _seed_inference(db_session, image_id=img.id, model_id=model.id)
    await db_session.commit()

    await _async_sync_detections(inf.id)

    rows = await clickhouse_client.query(
        "SELECT count() AS n FROM fact_detection WHERE inference_id = %(id)s",
        {"id": str(inf.id)},
    )
    assert rows == [{"n": 0}]


# ── fact_scan_batch round-trip + ReplacingMergeTree dedup ──────────────────


@pytest.mark.usefixtures("_truncate_clickhouse")
async def test_sync_scan_batch_dedups_via_replacing_merge_tree(
    db_session: AsyncSession,
    clickhouse_client: Any,
) -> None:
    """At-least-once delivery is safe: two consecutive syncs of the same
    batch collapse to one row via ``FINAL`` (ReplacingMergeTree)."""
    user = await _seed_user(db_session, email="rmt@e.com")
    batch = await _seed_batch(db_session, user_id=user.id)
    await db_session.commit()

    # First sync — pending status.
    await _async_sync_scan_batch(batch.id)

    # Mutate status; second sync should overwrite the row at FINAL.
    batch.status = "succeeded"
    await db_session.commit()
    await _async_sync_scan_batch(batch.id)

    rows = await clickhouse_client.query(
        "SELECT batch_id, status, geo_country_code "
        "FROM fact_scan_batch FINAL WHERE batch_id = %(id)s",
        {"id": str(batch.id)},
    )
    assert len(rows) == 1
    assert rows[0]["status"] == "succeeded"
    assert rows[0]["geo_country_code"] == "EG"
