"""Integration tests for app.crud against a real PostgreSQL database."""
import uuid

import pytest

from app import crud
from app.models import User, ScanBatch, ProcessingStatus

pytestmark = pytest.mark.integration


def _make_user(db):
    fp = uuid.uuid4().hex
    return crud.get_or_create_guest_user(db, fp), fp


def test_get_or_create_guest_user_is_idempotent(db_session):
    fp = uuid.uuid4().hex
    u1 = crud.get_or_create_guest_user(db_session, fp)
    u2 = crud.get_or_create_guest_user(db_session, fp)
    assert u1.id == u2.id
    assert u1.is_guest is True


def test_get_or_create_guest_user_rejects_empty_fingerprint(db_session):
    with pytest.raises(ValueError):
        crud.get_or_create_guest_user(db_session, "")


def test_get_user_by_fingerprint_none_for_unknown(db_session):
    assert crud.get_user_by_fingerprint(db_session, uuid.uuid4().hex) is None


def test_get_user_by_fingerprint_none_for_empty(db_session):
    assert crud.get_user_by_fingerprint(db_session, "") is None


def test_batches_and_stats_math(db_session):
    user, _ = _make_user(db_session)
    # Create two completed batches with known seed counts.
    b1 = ScanBatch(user_id=user.id, status=ProcessingStatus.COMPLETED,
                   total_seeds=10, bad_seeds_count=4, avg_confidence_score=0.9,
                   processing_duration_ms=100)
    b2 = ScanBatch(user_id=user.id, status=ProcessingStatus.COMPLETED,
                   total_seeds=20, bad_seeds_count=5, avg_confidence_score=0.8,
                   processing_duration_ms=200)
    db_session.add_all([b1, b2])
    db_session.commit()

    batches, total = crud.get_user_batches(db_session, user.id)
    assert total == 2
    # good = total - bad
    by_id = {b["id"]: b for b in batches}
    assert by_id[b1.id]["good_seeds_count"] == 6
    assert by_id[b1.id]["good_percentage"] == pytest.approx(60.0)

    stats = crud.get_user_statistics(db_session, user.id)
    assert stats["total_batches"] == 2
    assert stats["total_seeds_analyzed"] == 30
    assert stats["total_bad_seeds"] == 9
    assert stats["total_good_seeds"] == 21
    assert stats["overall_good_percentage"] == pytest.approx(70.0)
    assert stats["batches_by_status"]["COMPLETED"] == 2


def test_get_user_batches_invalid_status_returns_empty(db_session):
    user, _ = _make_user(db_session)
    batches, total = crud.get_user_batches(db_session, user.id, status="NONSENSE")
    assert batches == [] and total == 0


def test_get_user_statistics_empty_user(db_session):
    user, _ = _make_user(db_session)
    stats = crud.get_user_statistics(db_session, user.id)
    assert stats["total_batches"] == 0
    assert stats["overall_good_percentage"] == 0.0


def test_batch_ownership_isolation(db_session):
    user_a, _ = _make_user(db_session)
    user_b, _ = _make_user(db_session)
    batch = ScanBatch(user_id=user_a.id, status=ProcessingStatus.COMPLETED, total_seeds=1, bad_seeds_count=0)
    db_session.add(batch)
    db_session.commit()
    # owner can fetch
    assert crud.get_batch_by_id_and_user(db_session, batch.id, user_a.id) is not None
    # other user cannot
    assert crud.get_batch_by_id_and_user(db_session, batch.id, user_b.id) is None
    # detections for non-owner return empty (defense in depth)
    assert crud.get_batch_detections(db_session, batch.id, user_b.id) == []
