"""Unit tests for the DWH dispatch helper + ORM-to-dim builders.

Real worker plumbing (PG session, CH client) is exercised in the
integration tier. This file pins the small, pure pieces:

* :func:`dispatch_after_commit` swallows broker errors so a Redis
  outage never poisons an already-committed API response.
* :func:`_dim_user`, :func:`_dim_model`, :func:`_dim_seed_type` produce
  the exact dim row shape expected by ClickHouse.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest

from seedbank.core import metrics
from seedbank.core.exceptions import NotFoundError
from seedbank.workers.tasks import dwh as dwh_module
from seedbank.workers.tasks.dwh import (
    DWH_QUEUE,
    SYNC_INFERENCE,
    _dim_model,
    _dim_seed_type,
    _dim_user,
    _run_timed,
    _scrub_broker_url,
    dispatch_after_commit,
)


def _duration_count(task: str, result: str) -> float:
    """Read the histogram's ``_count`` from rendered samples.

    Histogram label children don't expose ``_count`` directly — the count
    lives in the ``*_count`` sample produced by ``collect()``.
    """
    target = {"task": task, "result": result}
    for m in metrics.DWH_TASK_DURATION.collect():
        for s in m.samples:
            if s.name.endswith("_count") and s.labels == target:
                return s.value
    return 0.0


def _dispatch_counter(task: str, result: str) -> float:
    return metrics.DWH_DISPATCH.labels(task=task, result=result)._value.get()


pytestmark = pytest.mark.unit


# ── dispatch_after_commit ──────────────────────────────────────────────────


def test_dispatch_after_commit_calls_celery_send_task() -> None:
    inf_id = str(uuid4())
    with patch.object(dwh_module.celery_app, "send_task") as send:
        dispatch_after_commit(SYNC_INFERENCE, inf_id)
    send.assert_called_once_with(SYNC_INFERENCE, args=[inf_id], queue=DWH_QUEUE)


def test_dispatch_after_commit_swallows_broker_failures() -> None:
    """A Redis outage must NOT propagate into the commit-then-dispatch
    call site — the OLTP write is already durable; losing the warehouse
    delta is recoverable via backfill."""
    with patch.object(
        dwh_module.celery_app, "send_task", side_effect=ConnectionError("redis down")
    ):
        dispatch_after_commit(SYNC_INFERENCE, str(uuid4()))  # must not raise


def test_dispatch_after_commit_short_circuits_when_dwh_disabled() -> None:
    """When ``dwh_enabled=False`` the helper is a no-op: ``send_task`` must
    NEVER be invoked. This is the kill-switch the e2e test path relies on
    so eager-Celery doesn't inline-invoke a sync task against an absent
    ClickHouse container."""
    fake_settings = SimpleNamespace(dwh_enabled=False)
    with (
        patch.object(dwh_module, "get_settings", return_value=fake_settings),
        patch.object(dwh_module.celery_app, "send_task") as send,
    ):
        dispatch_after_commit(SYNC_INFERENCE, str(uuid4()))
    send.assert_not_called()


# ── Dispatch counter (Finding #5) ──────────────────────────────────────────


def test_dispatch_counter_ticks_on_success() -> None:
    before = _dispatch_counter(SYNC_INFERENCE, "ok")
    with patch.object(dwh_module.celery_app, "send_task"):
        dispatch_after_commit(SYNC_INFERENCE, str(uuid4()))
    after = _dispatch_counter(SYNC_INFERENCE, "ok")
    assert after - before == 1


def test_dispatch_counter_ticks_on_broker_error() -> None:
    """A broker failure must record an ``error`` tick — that's the alert
    surface operators wire up for Finding #5."""
    before = _dispatch_counter(SYNC_INFERENCE, "error")
    with patch.object(
        dwh_module.celery_app, "send_task", side_effect=ConnectionError("redis down")
    ):
        dispatch_after_commit(SYNC_INFERENCE, str(uuid4()))
    after = _dispatch_counter(SYNC_INFERENCE, "error")
    assert after - before == 1


def test_dispatch_counter_records_disabled_state() -> None:
    """``dwh_enabled=False`` is a deliberate skip, not an outage —
    distinguish via the ``disabled`` label so the failure-rate alert
    doesn't fire on dev stacks where the kill switch is off."""
    fake_settings = SimpleNamespace(dwh_enabled=False)
    before = _dispatch_counter(SYNC_INFERENCE, "disabled")
    with (
        patch.object(dwh_module, "get_settings", return_value=fake_settings),
        patch.object(dwh_module.celery_app, "send_task"),
    ):
        dispatch_after_commit(SYNC_INFERENCE, str(uuid4()))
    after = _dispatch_counter(SYNC_INFERENCE, "disabled")
    assert after - before == 1


# ── ORM → DimRow builders ──────────────────────────────────────────────────


def _ts(year: int = 2026) -> datetime:
    return datetime(year, 1, 1, 12, 0, 0, tzinfo=UTC)


def test_dim_user_maps_orm_fields() -> None:
    user = SimpleNamespace(
        id=uuid4(),
        email="x@y.com",
        role="ai_developer",
        is_active=True,
        is_verified=False,
        created_at=_ts(),
        updated_at=_ts(2026),
    )
    row = _dim_user(user)
    assert row.user_id == user.id
    assert row.email == "x@y.com"
    assert row.role == "ai_developer"
    assert row.is_active is True
    assert row.is_verified is False
    assert row.created_at.tzinfo is UTC


def test_dim_model_preserves_nullable_seed_type() -> None:
    model = SimpleNamespace(
        id=uuid4(),
        name="resnet18",
        version="v1",
        kind="classification",
        backend="torch_local",
        seed_type_id=None,
        status="production",
        created_at=_ts(),
        updated_at=_ts(),
    )
    row = _dim_model(model)
    assert row.seed_type_id is None
    assert row.status == "production"
    assert row.kind == "classification"


## ── _run_timed (DWH_TASK_DURATION) ─────────────────────────────────────────


def test_run_timed_records_ok_on_clean_return() -> None:
    """Happy path: histogram count delta == 1 with ``result="ok"``."""
    task = "seedbank.dwh.test_ok"

    async def _inner(_uuid):
        return None

    before = _duration_count(task, "ok")
    _run_timed(task, _inner, str(uuid4()))
    after = _duration_count(task, "ok")
    assert after - before == 1


def test_run_timed_records_not_found_and_reraises() -> None:
    """``NotFoundError`` is the non-retryable label; outer call must
    re-raise so Celery's ack semantics see the failure."""
    task = "seedbank.dwh.test_not_found"

    async def _inner(_uuid):
        raise NotFoundError("missing")

    before = _duration_count(task, "not_found")
    with pytest.raises(NotFoundError):
        _run_timed(task, _inner, str(uuid4()))
    after = _duration_count(task, "not_found")
    assert after - before == 1


def test_run_timed_records_error_and_reraises_on_generic_exception() -> None:
    """Generic exceptions land on ``result="error"`` — the alert surface
    operators wire to a retry-driving condition."""
    task = "seedbank.dwh.test_error"

    async def _inner(_uuid):
        raise RuntimeError("boom")

    before = _duration_count(task, "error")
    with pytest.raises(RuntimeError, match="boom"):
        _run_timed(task, _inner, str(uuid4()))
    after = _duration_count(task, "error")
    assert after - before == 1


# ── _scrub_broker_url ──────────────────────────────────────────────────────


def test_scrub_broker_url_masks_redis_credentials() -> None:
    msg = "ConnectionError on redis://:secret@redis:6379/0"
    out = _scrub_broker_url(msg)
    assert "secret" not in out
    assert "redis://***@redis:6379/0" in out


def test_scrub_broker_url_masks_amqp_credentials() -> None:
    msg = "BrokerError at amqp://guest:guest@rabbit:5672"
    out = _scrub_broker_url(msg)
    assert "guest:guest" not in out
    assert "amqp://***@rabbit:5672" in out


def test_scrub_broker_url_passthrough_when_no_url() -> None:
    msg = "plain old error message"
    assert _scrub_broker_url(msg) == msg


def test_dim_seed_type_preserves_decimal_threshold() -> None:
    st = SimpleNamespace(
        id=uuid4(),
        code="coffee",
        display_name="Coffee",
        default_confidence_threshold=Decimal("0.7000"),
        created_at=_ts(),
        updated_at=_ts(),
    )
    row = _dim_seed_type(st)
    assert isinstance(row.default_confidence_threshold, Decimal)
    assert row.default_confidence_threshold == Decimal("0.7000")
    assert row.code == "coffee"
