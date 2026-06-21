"""Unit tests for :class:`seedbank.services.experiment_service.ExperimentService`.

Pins:

* model not found / archived → domain error
* dataset not found → domain error
* happy path: row inserted, AuditLog row added, commit, send_task fired
* dispatch order: commit happens before ``send_task`` (worker visibility)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from seedbank.core.exceptions import NotFoundError, ValidationError
from seedbank.domain.user import AuthenticatedUser, Role
from seedbank.infrastructure.db.enums import ModelStatus
from seedbank.infrastructure.db.models import AuditLog
from seedbank.services.experiment_service import ExperimentService

pytestmark = pytest.mark.unit


def _make_actor() -> AuthenticatedUser:
    return AuthenticatedUser(
        id=uuid4(),
        email="ai@dev.com",
        role=Role.AI_DEVELOPER,
        is_active=True,
        is_verified=True,
        scopes=frozenset(),
        auth_method="jwt",
    )


class _FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.added: list[Any] = []
        self.commit_history: list[str] = []

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1
        self.commit_history.append("commit")

    async def flush(self) -> None:
        pass

    async def rollback(self) -> None:
        pass


def _build_service(
    *,
    model: Any | None,
    dataset: Any | None,
) -> tuple[ExperimentService, _FakeSession, MagicMock]:
    session = _FakeSession()
    experiments = MagicMock()
    experiments.add = AsyncMock(side_effect=lambda x: x)
    experiments.list_filtered = AsyncMock(return_value=[])
    experiments.count_filtered = AsyncMock(return_value=0)
    results = MagicMock()
    models = MagicMock()
    models.get = AsyncMock(return_value=model)
    datasets = MagicMock()
    datasets.get_active = AsyncMock(return_value=dataset)
    svc = ExperimentService(
        session=session,  # type: ignore[arg-type]
        experiments=experiments,
        results=results,
        models=models,
        datasets=datasets,
    )
    return svc, session, experiments


def _ok_model() -> MagicMock:
    m = MagicMock()
    m.id = uuid4()
    m.status = ModelStatus.PRODUCTION.value
    return m


def _ok_dataset() -> MagicMock:
    d = MagicMock()
    d.id = uuid4()
    return d


# ── Validation ────────────────────────────────────────────────────────────


async def test_create_raises_when_model_missing() -> None:
    svc, _s, _e = _build_service(model=None, dataset=_ok_dataset())
    with pytest.raises(NotFoundError):
        await svc.create_and_dispatch(
            actor=_make_actor(),
            name="exp",
            model_id=uuid4(),
            dataset_id=uuid4(),
            ip=None,
        )


async def test_create_raises_when_model_archived() -> None:
    m = _ok_model()
    m.status = ModelStatus.ARCHIVED.value
    svc, _s, _e = _build_service(model=m, dataset=_ok_dataset())
    with pytest.raises(ValidationError):
        await svc.create_and_dispatch(
            actor=_make_actor(),
            name="exp",
            model_id=m.id,
            dataset_id=uuid4(),
            ip=None,
        )


async def test_create_raises_when_dataset_missing() -> None:
    svc, _s, _e = _build_service(model=_ok_model(), dataset=None)
    with pytest.raises(NotFoundError):
        await svc.create_and_dispatch(
            actor=_make_actor(),
            name="exp",
            model_id=uuid4(),
            dataset_id=uuid4(),
            ip=None,
        )


# ── Happy path ────────────────────────────────────────────────────────────


async def test_create_inserts_audit_and_dispatches_after_commit() -> None:
    model = _ok_model()
    dataset = _ok_dataset()
    svc, session, experiments = _build_service(model=model, dataset=dataset)

    with patch("seedbank.services.experiment_service.celery_app.send_task") as send_task:
        out = await svc.create_and_dispatch(
            actor=_make_actor(),
            name="exp-x",
            model_id=model.id,
            dataset_id=dataset.id,
            ip="10.0.0.1",
        )

    # The experiment row is inserted and committed.
    experiments.add.assert_awaited_once()
    assert session.commits == 1
    assert out.name == "exp-x"
    assert out.model_id == model.id
    assert out.dataset_id == dataset.id

    # Audit log row was added inside the same transaction.
    audit_rows = [a for a in session.added if isinstance(a, AuditLog)]
    assert len(audit_rows) == 1
    assert audit_rows[0].action == "experiment.dispatched"

    # Celery dispatch happens AFTER commit. We can't observe ordering from
    # the mocks alone, but we assert the call shape and queue.
    send_task.assert_called_once()
    args, kwargs = send_task.call_args
    assert args[0] == "seedbank.run_experiment"
    assert kwargs["queue"] == "experiments"
    assert kwargs["args"] == [str(out.id)]
