# Decisions

Locked architectural decisions, each a short statement + the *why* + a link to
its authoritative home in `docs/`. Thin pointers, not copies — the depth lives in
the docs/ADR they reference. Not up for re-litigation unless the user reopens
them. Indexed from [`MEMORY.md`](MEMORY.md).

_Last updated: 2026-06-26_

## DWH is app-level dual-write, not CDC

Analytics land in ClickHouse via an **app-level dual-write**: when `dwh_enabled`,
the API/workers dispatch a Celery task (`workers/tasks/dwh.py`) that writes the
star schema. True logical-replication CDC is **deferred** — Postgres runs with
`wal_level=logical` and replication slots provisioned, but nothing consumes them.

**Why:** dual-write shipped the analytics path without standing up
Debezium/Kafka or a CDC consumer, keeping the stack lean (see [Lean
Compose](#lean-compose-without-degrading-quality)). The CDC seam is left open so
it can be added later without a schema change. Don't describe the DWH as CDC-fed
or propose Kafka/Debezium unless the user reopens it. Authoritative detail:
[`docs/revamp-status.md`](../../docs/revamp-status.md) Phase 8 and
[`docs/system-overview.md`](../../docs/system-overview.md) §4.10. Related test
trap: [the 4 DWH xfail tests](known-issues.md#the-4-dwh-tests-xfail-51).

## Lean Compose, without degrading quality

The deployment target is Docker Compose, kept **"as light as possible WITHOUT
degrading quality."** Footprint matters; the non-negotiables do not get cut to
shrink it — observability, full auth, the test pyramid, and the ML platform all
stay.

**Why:** the owner wants a laptop-class machine to `make up && make seed &&
make test` comfortably, without trading away production-grade behaviour. So:
multi-stage Dockerfile with **torch/torchvision only in the inference worker
image**, never the `api` image (~1.6 GB difference — see [analyze needs a
model](known-issues.md#analyze-needs-a-promoted-detection-model)); no
Kafka/ZooKeeper/Debezium (that's why the DWH is [dual-write, not
CDC](#dwh-is-app-level-dual-write-not-cdc)); single-node ClickHouse; alpine bases
where stable. Authoritative detail:
[`docs/operations.md`](../../docs/operations.md) and the `Dockerfile` stage table
in [`docs/system-overview.md`](../../docs/system-overview.md) §7.4.

## Hard reset from the prototype

The production codebase under `src/seedbank/` is a **hard reset** of an earlier
ML prototype, not a refactor of it. The old code is archived to `legacy/`
(gitignored working tree, kept in history for reference only). The only assets
that carried over are the trained `.pth` weights — and even those now live in
MinIO, not git.

**Why:** the prototype mixed routing, ML orchestration, DB writes, and image I/O
in one 1,600-line module with placebo auth and a hardcoded API key. A surgical
refactor would have embedded those patterns; a clean rebuild on the layered
architecture was the call. So: **never import from `legacy/`** or patch it to fix
prod — if you need a piece, port it into the live surface and delete the archived
copy. Build under `src/seedbank/` per the layered pillars in `CLAUDE.md`; don't
map features onto the old file structure. The one thing reused verbatim is the
architecture math in the model builders (copied into
`infrastructure/ml/builders/`), which was correct.
