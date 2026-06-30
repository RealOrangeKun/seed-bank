---
description: Generate a new Alembic migration with the project's conventions; opens the file for review afterwards
argument-hint: "<short message in quotes, e.g. 'add widget table'>"
allowed-tools: Read, Glob, Grep, Bash, Edit
---

# New migration: $ARGUMENTS

Wrap `alembic revision --autogenerate` and force a human-quality review.
Autogenerate is a *starting point* — it diffs `Base.metadata` against the DB and
reliably misses partial indexes, CHECK constraints, `comment=`, and FK indexes.
Treat the generated file as a draft you finish by hand. The `db-migration` skill
is the deep reference for the hand-fixes and zero-downtime patterns; this command
is the fast loop.

## Steps

1. Verify the dev DB is up so autogenerate can introspect it:
   `docker compose ps postgres | grep -q "running\|healthy"` (start it with `make up` if not).
2. Generate:
   ```bash
   alembic revision --autogenerate -m $ARGUMENTS
   ```
3. Find the new revision under `alembic/versions/` (newest mtime) and **read it**.
4. Apply the project conventions (see the `db-migration` skill for the full list) —
   the ones autogenerate routinely drops:
   - **Index every FK** — Postgres does not create them automatically, and joins/
     `ON DELETE CASCADE` scans get slow without them.
   - **CHECK constraints on enum-like text columns** so bad states can't be written.
   - **UUIDv7 PKs** — confirm the model used `uuid7()` from `core/ids.py`, not a
     server default; the value is generated app-side.
   - **`Numeric`, not `Float`**, for confidence `(5,4)` and normalized bbox `(7,6)` —
     money-style precision, no binary-float drift.
   - **TZ-aware timestamps** (`DateTime(timezone=True)`).
   - **A working `downgrade()`** — every schema migration is reversible; a data
     migration lives in its own revision and never mixes DDL with bulk DML.
   - For an index on an already-populated table, set `transactional_ddl = False`
     and create it `CONCURRENTLY` to avoid locking writes.
5. Round-trip on the dev DB to prove upgrade and downgrade both run:
   ```bash
   alembic upgrade head
   alembic downgrade -1
   alembic upgrade head
   ```
6. Summarize for the user: revision file path, the changes autogenerate detected,
   the fixes you applied (or "no fixes needed"), and the round-trip result.

## If autogenerate produced an empty migration

Either the model and DB are already in sync, or autogenerate didn't notice the
change (common for `comment=`, partial indexes, CHECK constraints — it can't see
those). Say so explicitly so the user doesn't read silence as success; write the
DDL by hand if the change is one autogenerate can't detect.

## If autogenerate flagged drops you didn't intend

Stop — don't apply. The usual cause is a model file that isn't imported, so its
table is absent from `Base.metadata` and autogenerate "sees" it as deleted. Tell
the user which tables/columns it wants to drop and confirm before proceeding;
applying it blind would drop live data.
