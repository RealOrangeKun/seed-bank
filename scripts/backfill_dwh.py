"""Replay missed OLTP→ClickHouse deltas.

The dual-write path (:mod:`seedbank.workers.tasks.dwh`) is best-effort:
a Redis blip during ``dispatch_after_commit`` silently drops a warehouse
delta. The OLTP commit always wins, but the warehouse can drift. This
script is the recovery hammer.

Reads source rows from Postgres in a chosen time window and either:

* dispatches the matching ``seedbank.dwh.sync_*`` Celery task per row
  (default — workers do the writes, broker is at-least-once), or
* runs the task body inline in this process (``--inline`` — useful when
  the worker fleet is down or the operator wants synchronous failures).

Idempotent end-to-end: the warehouse uses ``ReplacingMergeTree`` keyed
on the source PK + ``_ingested_at``, so re-running over an already-synced
window collapses cleanly at merge time. Re-run is the safe move.

Usage::

    # Last 24h, all kinds, dispatch via Celery (the typical case):
    python scripts/backfill_dwh.py

    # Specific window:
    python scripts/backfill_dwh.py --since 2026-04-01T00:00:00Z --until 2026-04-02T00:00:00Z

    # Just inferences + their detections:
    python scripts/backfill_dwh.py --kinds inferences

    # Synchronous mode (bypasses Celery, fails loud, slower):
    python scripts/backfill_dwh.py --inline

    # See what would happen without writing anything:
    python scripts/backfill_dwh.py --dry-run

Exit code 0 on success, non-zero only on connection / SQL failures —
per-row warehouse errors during ``--inline`` are logged and counted but
do not abort the run, so partial recovery is preferred over zero.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable
    from uuid import UUID

    from sqlalchemy.orm import InstrumentedAttribute

from seedbank.core.config import get_settings
from seedbank.core.logging import get_logger
from seedbank.infrastructure.db.models import (
    Experiment,
    Inference,
    ScanBatch,
)
from seedbank.workers.celery_app import celery_app
from seedbank.workers.tasks.dwh import (
    DWH_QUEUE,
    SYNC_DETECTIONS,
    SYNC_EXPERIMENT_RESULTS,
    SYNC_INFERENCE,
    SYNC_SCAN_BATCH,
    _async_sync_detections,
    _async_sync_experiment_results,
    _async_sync_inference,
    _async_sync_scan_batch,
)

log = get_logger("seedbank.backfill_dwh")


# ── CLI ────────────────────────────────────────────────────────────────────


_KINDS = ("inferences", "scan_batches", "experiments")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--since",
        type=_parse_iso,
        default=None,
        help="Lower bound (inclusive). Default: now - 24h.",
    )
    p.add_argument(
        "--until",
        type=_parse_iso,
        default=None,
        help="Upper bound (exclusive). Default: now.",
    )
    p.add_argument(
        "--kinds",
        nargs="+",
        choices=(*_KINDS, "all"),
        default=["all"],
        help="Which entity kinds to backfill. Default: all.",
    )
    p.add_argument(
        "--inline",
        action="store_true",
        help="Run task bodies in this process instead of dispatching to Celery.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print counts only; no dispatches and no inline writes.",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Rows pulled from PG per page. Default: 500.",
    )
    return p.parse_args()


def _parse_iso(s: str) -> datetime:
    """Accept ``YYYY-MM-DDTHH:MM:SS[+offset]`` or trailing ``Z``."""
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


# ── Counters ───────────────────────────────────────────────────────────────


class _Counters:
    __slots__ = ("dispatched", "inline_err", "inline_ok")

    def __init__(self) -> None:
        self.dispatched = 0
        self.inline_ok = 0
        self.inline_err = 0


# ── Driver ─────────────────────────────────────────────────────────────────


async def _iter_ids(
    session_factory: async_sessionmaker[AsyncSession],
    column: InstrumentedAttribute[Any],
    model: type[Any],
    since: datetime,
    until: datetime,
    batch_size: int,
    extra_where: list[Any] | None = None,
) -> AsyncIterator[tuple[UUID, datetime]]:
    """Stream PKs in time-column order, paged so the working set stays bounded.

    ``extra_where`` is appended to the WHERE clause unchanged — used by the
    experiment "fallback to created_at" pass to gate on ``finished_at IS NULL``
    so the two passes cover disjoint sets and never double-count.
    """
    cursor: datetime | None = since
    last_id: UUID | None = None
    while True:
        async with session_factory() as session:
            stmt = (
                select(model.id, column)
                .where(column >= cursor)
                .where(column < until)
                .order_by(column.asc(), model.id.asc())
                .limit(batch_size)
            )
            for predicate in extra_where or ():
                stmt = stmt.where(predicate)
            # Skip the boundary row from the previous page when cursor + last_id repeat.
            if last_id is not None:
                stmt = stmt.where((column > cursor) | ((column == cursor) & (model.id > last_id)))
            rows = list((await session.execute(stmt)).all())
        if not rows:
            return
        for row in rows:
            yield row[0], row[1]
        last_row = rows[-1]
        last_id = last_row[0]
        cursor = last_row[1]


async def _run_one(
    *,
    inline: bool,
    dry_run: bool,
    counters: _Counters,
    task_name: str,
    inline_fn: Callable[[UUID], Awaitable[None]],
    arg_uuid: UUID,
) -> None:
    if dry_run:
        return
    if inline:
        try:
            await inline_fn(arg_uuid)
            counters.inline_ok += 1
        except Exception as exc:
            counters.inline_err += 1
            log.warning(
                "backfill.inline_failed",
                task=task_name,
                arg=str(arg_uuid),
                error=repr(exc),
            )
    else:
        try:
            celery_app.send_task(task_name, args=[str(arg_uuid)], queue=DWH_QUEUE)
            counters.dispatched += 1
        except Exception as exc:
            log.error("backfill.dispatch_failed", task=task_name, error=repr(exc))
            raise


async def _backfill_inferences(
    sf: async_sessionmaker[AsyncSession],
    since: datetime,
    until: datetime,
    batch_size: int,
    inline: bool,
    dry_run: bool,
    counters: _Counters,
) -> int:
    n = 0
    async for inf_id, _ts in _iter_ids(
        sf, Inference.occurred_at, Inference, since, until, batch_size
    ):
        # Each Inference fans out to two CH writes — fact_inference + fact_detection.
        await _run_one(
            inline=inline,
            dry_run=dry_run,
            counters=counters,
            task_name=SYNC_INFERENCE,
            inline_fn=_async_sync_inference,
            arg_uuid=inf_id,
        )
        await _run_one(
            inline=inline,
            dry_run=dry_run,
            counters=counters,
            task_name=SYNC_DETECTIONS,
            inline_fn=_async_sync_detections,
            arg_uuid=inf_id,
        )
        n += 1
    log.info("backfill.kind_done", kind="inferences", source_rows=n)
    return n


async def _backfill_scan_batches(
    sf: async_sessionmaker[AsyncSession],
    since: datetime,
    until: datetime,
    batch_size: int,
    inline: bool,
    dry_run: bool,
    counters: _Counters,
) -> int:
    n = 0
    async for bid, _ts in _iter_ids(
        sf, ScanBatch.submitted_at, ScanBatch, since, until, batch_size
    ):
        await _run_one(
            inline=inline,
            dry_run=dry_run,
            counters=counters,
            task_name=SYNC_SCAN_BATCH,
            inline_fn=_async_sync_scan_batch,
            arg_uuid=bid,
        )
        n += 1
    log.info("backfill.kind_done", kind="scan_batches", source_rows=n)
    return n


async def _backfill_experiments(
    sf: async_sessionmaker[AsyncSession],
    since: datetime,
    until: datetime,
    batch_size: int,
    inline: bool,
    dry_run: bool,
    counters: _Counters,
) -> int:
    # Experiments may finish well after they're created; gate on finished_at
    # when present, fall back to created_at otherwise. Rather than COALESCE
    # in SQL (kills index use), we run two passes over disjoint windows:
    #   pass A: finished_at ∈ [since, until)            (the typical case)
    #   pass B: finished_at IS NULL AND created_at ∈ [since, until)
    #            (experiments that crashed / are still running)
    # The IS NULL guard on pass B keeps the two sets disjoint so an
    # experiment is never dispatched twice.
    n = 0
    async for exp_id, _ts in _iter_ids(
        sf, Experiment.finished_at, Experiment, since, until, batch_size
    ):
        await _run_one(
            inline=inline,
            dry_run=dry_run,
            counters=counters,
            task_name=SYNC_EXPERIMENT_RESULTS,
            inline_fn=_async_sync_experiment_results,
            arg_uuid=exp_id,
        )
        n += 1
    async for exp_id, _ts in _iter_ids(
        sf,
        Experiment.created_at,
        Experiment,
        since,
        until,
        batch_size,
        extra_where=[Experiment.finished_at.is_(None)],
    ):
        await _run_one(
            inline=inline,
            dry_run=dry_run,
            counters=counters,
            task_name=SYNC_EXPERIMENT_RESULTS,
            inline_fn=_async_sync_experiment_results,
            arg_uuid=exp_id,
        )
        n += 1
    log.info("backfill.kind_done", kind="experiments", source_rows=n)
    return n


async def main() -> int:
    args = _parse_args()
    until = args.until or datetime.now(UTC)
    since = args.since or (until - timedelta(hours=24))
    if since >= until:
        log.error("backfill.bad_window", since=since.isoformat(), until=until.isoformat())
        return 2
    kinds = set(_KINDS) if "all" in args.kinds else set(args.kinds)

    log.info(
        "backfill.start",
        since=since.isoformat(),
        until=until.isoformat(),
        kinds=sorted(kinds),
        inline=args.inline,
        dry_run=args.dry_run,
    )

    settings = get_settings()
    if not settings.dwh_enabled and not args.inline:
        # Dispatching with the master flag off would be a no-op fleet-wide
        # because workers also honor it on the read path? No — the flag
        # only gates the dispatch helper at call sites. Workers still
        # process tasks. So this is fine; just warn loudly.
        log.warning(
            "backfill.dwh_disabled_warning",
            msg="settings.dwh_enabled is False; dispatched tasks will still run on workers",
        )

    engine = create_async_engine(str(settings.postgres_dsn), future=True)
    sf = async_sessionmaker(bind=engine, expire_on_commit=False)
    counters = _Counters()

    try:
        if "scan_batches" in kinds:
            await _backfill_scan_batches(
                sf, since, until, args.batch_size, args.inline, args.dry_run, counters
            )
        if "inferences" in kinds:
            await _backfill_inferences(
                sf, since, until, args.batch_size, args.inline, args.dry_run, counters
            )
        if "experiments" in kinds:
            await _backfill_experiments(
                sf, since, until, args.batch_size, args.inline, args.dry_run, counters
            )
    finally:
        await engine.dispose()

    log.info(
        "backfill.done",
        dispatched=counters.dispatched,
        inline_ok=counters.inline_ok,
        inline_err=counters.inline_err,
    )
    # Non-zero exit only when inline mode hit failures the operator should see.
    return 1 if counters.inline_err > 0 else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
