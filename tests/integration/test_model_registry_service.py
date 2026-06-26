"""Integration tests for ModelRegistryService.

Exercises the full status state machine against a real Postgres (testcontainer)
plus a stub MinIO storage that returns ``True`` for every existence check
(so the verification doesn't fight the test).
"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from seedbank.core.exceptions import ConflictError, ValidationError
from seedbank.core.ids import uuid7
from seedbank.infrastructure.db.enums import (
    ModelBackend,
    ModelKind,
    ModelStatus,
    UserRole,
)
from seedbank.infrastructure.db.models import ModelArtifact, SeedType, User
from seedbank.infrastructure.db.repositories import ModelArtifactRepository
from seedbank.services.model_registry_service import (
    ModelRegistryService,
    RegisterModelInput,
)

pytestmark = pytest.mark.integration


class _StubStorage:
    """Stand-in for MinioStorage: every artifact_uri 'exists'."""

    async def object_exists(self, bucket: str, key: str) -> bool:
        return True


async def _seed_user(db_session: AsyncSession) -> User:
    """Create one ai_developer user with a UUID-derived email.

    Uses ``uuid7()`` rather than ``id(db_session)`` because tests that call
    this helper twice within a single test (e.g. duplicate-rejection
    coverage) would otherwise collide on ``uq_users_email``.
    """
    user = User(
        email=f"dev-{uuid7()}@example.com",
        hashed_password="bcrypt$irrelevant",
        role=UserRole.AI_DEVELOPER.value,
    )
    db_session.add(user)
    await db_session.flush()
    return user


def _service(db_session: AsyncSession) -> ModelRegistryService:
    return ModelRegistryService(
        session=db_session,
        models=ModelArtifactRepository(db_session),
        storage=_StubStorage(),  # type: ignore[arg-type]
    )


async def _register(
    db_session: AsyncSession,
    *,
    name: str,
    version: str,
    user: User | None = None,
) -> ModelArtifact:
    """Register a model. Pass ``user`` to share one actor across calls
    (avoiding the unique-email constraint when the test issues multiple
    registrations); otherwise a fresh user is seeded."""
    if user is None:
        user = await _seed_user(db_session)
    svc = _service(db_session)
    return await svc.register(
        actor_id=user.id,
        payload=RegisterModelInput(
            name=name,
            version=version,
            kind=ModelKind.DETECTION,
            backend=ModelBackend.TORCH_LOCAL,
            artifact_uri=f"{name}/{version}/weights.pth",
        ),
    )


async def test_promote_through_full_state_machine(db_session: AsyncSession) -> None:
    user = await _seed_user(db_session)
    svc = _service(db_session)
    row = await svc.register(
        actor_id=user.id,
        payload=RegisterModelInput(
            name="m-fsm",
            version="v1",
            kind=ModelKind.DETECTION,
            backend=ModelBackend.TORCH_LOCAL,
            artifact_uri="m-fsm/v1/weights.pth",
        ),
    )
    assert row.status == ModelStatus.REGISTERED.value

    row = await svc.change_status(actor_id=user.id, model_id=row.id, new_status=ModelStatus.STAGING)
    assert row.status == ModelStatus.STAGING.value

    row = await svc.change_status(
        actor_id=user.id, model_id=row.id, new_status=ModelStatus.PRODUCTION
    )
    assert row.status == ModelStatus.PRODUCTION.value

    row = await svc.change_status(
        actor_id=user.id, model_id=row.id, new_status=ModelStatus.ARCHIVED
    )
    assert row.status == ModelStatus.ARCHIVED.value


async def test_illegal_transition_raises(db_session: AsyncSession) -> None:
    row = await _register(db_session, name="m-illegal", version="v1")
    svc = _service(db_session)
    user_id = row.created_by
    assert user_id is not None
    # registered → production is illegal (must go through staging).
    with pytest.raises(ValidationError):
        await svc.change_status(
            actor_id=user_id, model_id=row.id, new_status=ModelStatus.PRODUCTION
        )


async def test_promotion_archives_incumbent(db_session: AsyncSession) -> None:
    user = await _seed_user(db_session)
    svc = _service(db_session)
    old = await svc.register(
        actor_id=user.id,
        payload=RegisterModelInput(
            name="incumbent",
            version="v1",
            kind=ModelKind.DETECTION,
            backend=ModelBackend.TORCH_LOCAL,
            artifact_uri="incumbent/v1/weights.pth",
        ),
    )
    await svc.change_status(actor_id=user.id, model_id=old.id, new_status=ModelStatus.STAGING)
    await svc.change_status(actor_id=user.id, model_id=old.id, new_status=ModelStatus.PRODUCTION)

    new = await svc.register(
        actor_id=user.id,
        payload=RegisterModelInput(
            name="challenger",
            version="v1",
            kind=ModelKind.DETECTION,
            backend=ModelBackend.TORCH_LOCAL,
            artifact_uri="challenger/v1/weights.pth",
        ),
    )
    await svc.change_status(actor_id=user.id, model_id=new.id, new_status=ModelStatus.STAGING)
    await svc.change_status(actor_id=user.id, model_id=new.id, new_status=ModelStatus.PRODUCTION)

    refreshed_old = await svc.get(old.id)
    refreshed_new = await svc.get(new.id)
    assert refreshed_old.status == ModelStatus.ARCHIVED.value
    assert refreshed_new.status == ModelStatus.PRODUCTION.value


async def test_duplicate_name_version_rejected(db_session: AsyncSession) -> None:
    user = await _seed_user(db_session)
    await _register(db_session, name="dup-model", version="v1", user=user)
    with pytest.raises(ConflictError):
        await _register(db_session, name="dup-model", version="v1", user=user)


async def test_partial_unique_blocks_two_productions(db_session: AsyncSession) -> None:
    """The DB partial-unique index is the safety net if the service skipped
    the auto-archive step. We simulate by inserting raw rows.

    Both rows share the same ``(kind, seed_type_id)`` pair — a real
    ``seed_type_id`` (not NULL), because Postgres treats NULLs in a unique
    index as distinct by default, and the partial index this test pins is
    meant to catch the duplicate-production-per-segment case where the
    segment is fully specified.
    """
    user = await _seed_user(db_session)
    seed_type = SeedType(code="maize-test", display_name="Maize (test)")
    db_session.add(seed_type)
    await db_session.flush()

    common = dict(
        version="v1",
        kind=ModelKind.DETECTION.value,
        backend=ModelBackend.TORCH_LOCAL.value,
        status=ModelStatus.PRODUCTION.value,
        seed_type_id=seed_type.id,
        created_by=user.id,
    )
    a = ModelArtifact(name="raw-a", artifact_uri="raw-a/v1/weights.pth", **common)
    b = ModelArtifact(name="raw-b", artifact_uri="raw-b/v1/weights.pth", **common)
    db_session.add(a)
    await db_session.flush()
    db_session.add(b)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()
