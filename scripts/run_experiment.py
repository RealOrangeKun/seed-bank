"""CLI: run an offline evaluation experiment (model x dataset).

Usage::

    python scripts/run_experiment.py \
        --name "coffee-v3 vs holdout" \
        --model-id 0192... \
        --dataset-id 0192... \
        --actor-email dev@seedbank.dev \
        --wait

Like ``register_model.py`` this runs **directly against the service layer**
(no HTTP), so it can be invoked from the worker/CLI image without an admin
API key. It dispatches the experiment onto the ``experiments`` Celery queue;
the ``worker-cpu`` worker actually executes it. With ``--wait`` the CLI polls
the experiment row until it reaches a terminal state and prints the summary
metrics. Read the full per-model view from ``GET /api/v1/models/{id}/performance``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from seedbank.core.config import get_settings
from seedbank.domain.user import AuthenticatedUser, Role
from seedbank.infrastructure.db.enums import ExperimentStatus
from seedbank.infrastructure.db.repositories import (
    DatasetRepository,
    ExperimentRepository,
    ExperimentResultRepository,
    ModelArtifactRepository,
    UserRepository,
)
from seedbank.services.experiment_service import ExperimentService

if TYPE_CHECKING:
    from seedbank.infrastructure.db.models import User

_TERMINAL = frozenset({ExperimentStatus.SUCCEEDED.value, ExperimentStatus.FAILED.value})


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--name", required=True, help="Human-readable experiment name.")
    p.add_argument("--model-id", required=True, type=UUID)
    p.add_argument("--dataset-id", required=True, type=UUID)
    p.add_argument(
        "--actor-email",
        required=True,
        help="Email of the ai_developer/admin running this (must exist; audit + creator).",
    )
    p.add_argument(
        "--wait",
        action="store_true",
        help="Poll until the experiment reaches a terminal state, then print metrics.",
    )
    p.add_argument("--timeout", type=int, default=600, help="Max seconds to wait (with --wait).")
    p.add_argument("--poll-interval", type=int, default=5, help="Seconds between polls.")
    return p.parse_args()


def _actor_from(user: User) -> AuthenticatedUser:
    # Build the framework-free actor snapshot the service expects (the same
    # shape api.deps.current_user produces from an ORM User row).
    return AuthenticatedUser(
        id=user.id,
        email=user.email,
        role=Role(user.role),
        is_active=user.is_active,
        is_verified=user.is_verified,
    )


def _service(session: AsyncSession) -> ExperimentService:
    return ExperimentService(
        session=session,
        experiments=ExperimentRepository(session),
        results=ExperimentResultRepository(session),
        models=ModelArtifactRepository(session),
        datasets=DatasetRepository(session),
    )


async def _run(args: argparse.Namespace) -> int:
    settings = get_settings()
    engine = create_async_engine(str(settings.postgres_dsn), future=True)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with sm() as session:
            actor_row = await UserRepository(session).get_by_email(args.actor_email)
            if actor_row is None:
                print(f"actor not found: {args.actor_email}", file=sys.stderr)
                return 2
            actor = _actor_from(actor_row)
            experiment = await _service(session).create_and_dispatch(
                actor=actor,
                name=args.name,
                model_id=args.model_id,
                dataset_id=args.dataset_id,
                ip=None,
            )
        experiment_id = experiment.id
        print(f"dispatched experiment {experiment_id} (status=pending)")

        if not args.wait:
            print("not waiting; poll GET /api/v1/experiments/{id} or re-run with --wait.")
            return 0

        loop = asyncio.get_running_loop()
        deadline = loop.time() + args.timeout
        while loop.time() < deadline:
            async with sm() as session:
                row = await ExperimentRepository(session).get(experiment_id)
            if row is None:
                print(f"experiment {experiment_id} vanished", file=sys.stderr)
                return 1
            print(f"  status={row.status}")
            if row.status in _TERMINAL:
                print(f"duration_ms={row.duration_ms}")
                print(json.dumps(row.summary_metrics or {}, indent=2, default=str))
                return 0 if row.status == ExperimentStatus.SUCCEEDED.value else 1
            await asyncio.sleep(args.poll_interval)

        print(f"timed out after {args.timeout}s waiting for {experiment_id}", file=sys.stderr)
        return 1
    finally:
        await engine.dispose()


def main() -> int:
    return asyncio.run(_run(_parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
