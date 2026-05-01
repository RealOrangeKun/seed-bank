"""Unit tests for the DWH dispatch helper + ORM-to-dim builders.

Real worker plumbing (PG session, CH client) is exercised in the
integration tier. This file pins the small, pure pieces:

* :func:`dispatch_after_commit` swallows broker errors so a Redis
  outage never poisons an already-committed API response.
* :func:`_dim_user`, :func:`_dim_model`, :func:`_dim_seed_type` produce
  the exact dim row shape expected by ClickHouse.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest

from seedbank.workers.tasks import dwh as dwh_module
from seedbank.workers.tasks.dwh import (
    DWH_QUEUE,
    SYNC_INFERENCE,
    _dim_model,
    _dim_seed_type,
    _dim_user,
    dispatch_after_commit,
)

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
    with patch.object(dwh_module.celery_app, "send_task", side_effect=ConnectionError("redis down")):
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


# ── ORM → DimRow builders ──────────────────────────────────────────────────


def _ts(year: int = 2026) -> datetime:
    return datetime(year, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


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
    assert row.created_at.tzinfo is timezone.utc


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
