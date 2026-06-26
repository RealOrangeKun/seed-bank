---
name: db-migration
description: Alembic workflow for the seed-bank repo — autogenerate review, hand-fixes you must make, data migrations, and zero-downtime patterns. Use whenever schema changes.
---

# DB migration workflow

## Purpose

Turn a change to the SQLAlchemy models into a reviewed, reversible Alembic
revision. Autogenerate is a starting point — it diffs the ORM against the live
schema, but it can't see intent (indexes, constraints, defaults), so the
generated file is a draft you finish by hand.

## When to use

Any time you change the schema: a new table or column, an index, a constraint,
a type change, or a data backfill. Pairs with the `/new-migration` command,
which wraps autogenerate with our conventions and opens the file for review.

## Setup recap

- `alembic.ini` points at `alembic/`.
- `alembic/env.py` reads the URL from `Settings`, imports `Base.metadata` from
  `infrastructure/db/models.py`, and runs in **online async** mode against
  `asyncpg`.
- One revision per logical change — bundling two unrelated changes makes a
  partial rollback impossible and muddies the history.

## Steps

```bash
# 1. Edit src/seedbank/infrastructure/db/models.py.
# 2. Generate the revision (or use /new-migration "<msg>").
alembic revision --autogenerate -m "add widget table"

# 3. READ AND EDIT the generated file — this is the real work, not step 2.
$EDITOR alembic/versions/<rev>_add_widget_table.py

# 4. Test the upgrade.
alembic upgrade head

# 5. Test the downgrade, then re-upgrade — both must run cleanly.
alembic downgrade -1
alembic upgrade head

# 6. If the change touches existing data, test against a seeded DB too.
make seed && alembic upgrade head
```

The downgrade matters even if you never expect to run it: it's how a bad
deploy gets rolled back under pressure, and writing it forces you to confirm
the upgrade is actually reversible.

## What autogenerate gets wrong (always check)

These are the recurring gaps — autogenerate diffs structure, not intent, so
anything that lives in `__table_args__` or in DB-side SQL tends to be missed:

- **Indexes on FKs.** It creates the FK constraint but often skips the
  supporting index, so lookups and joins on the FK do sequential scans. Declare
  `Index("ix_widgets_owner_id", "owner_id")` in the model and confirm it lands
  in the migration.
- **Server defaults.** `default=` is Python-side only. For a DB-side default or
  a backfill you need `server_default=text("...")`; autogenerate doesn't always
  notice the difference.
- **CHECK constraints.** Declared via `__table_args__ = (CheckConstraint(...),)`
  — add them by hand. This is how a `status` string column gets the allowed-value
  guarantee that keeps bad rows out at the DB level.
- **Partial / functional indexes.** Missed entirely. Add e.g.
  `Index("...", "id", postgresql_where=text("deleted_at IS NULL"))` for the
  soft-delete predicate on user-visible aggregates.
- **ENUM type transitions.** Converting between a `String` + CHECK and a real
  Postgres ENUM needs manual `op.execute` blocks; autogenerate is messy here.
- **Column comments.** `mapped_column(..., comment="...")` is valuable for ops
  but autogenerate sometimes drops it.

## Conventions

- UUIDv7 PKs via `uuid7()` from `core/ids.py` (never `uuid4`) — sortable and
  index-friendly. `confidence` is `Numeric(5,4)`; normalized bounding boxes are
  `Numeric(7,6)`. Match these in the migration when the column is new.
- Soft delete (`SoftDeleteMixin`) only on user-visible aggregates —
  `scan_batches`, `datasets`, `users`. Internal tables hard-delete with
  `ON DELETE CASCADE`, so their FKs carry `ondelete="CASCADE"`.
- Timestamps are TZ-aware.
- Data migrations live in their own revision, never mixed with DDL — DDL and
  bulk DML have different locking and rollback characteristics, and separating
  them keeps each revision independently reversible.

## Patterns for safe schema changes

### Add a non-null column to a populated table

Three revisions, deployed in order, so no rolling-deploy window sees a column
the running code can't satisfy:

1. **Add as nullable** — `op.add_column("widgets", sa.Column("kind", sa.String(20), nullable=True))`.
2. **Backfill** — a separate revision: `op.execute("UPDATE widgets SET kind = 'standard' WHERE kind IS NULL")`. Add a `server_default` if one makes sense.
3. **Set NOT NULL** — `op.alter_column("widgets", "kind", nullable=False)`.

### Add an index on a large table

One revision, but build it without locking writes:

```python
def upgrade():
    op.execute("COMMIT")  # leave the implicit transaction
    op.execute("CREATE INDEX CONCURRENTLY ix_widgets_owner_id ON widgets (owner_id)")

def downgrade():
    op.execute("COMMIT")
    op.execute("DROP INDEX CONCURRENTLY ix_widgets_owner_id")
```

`CONCURRENTLY` can't run inside a transaction, so mark the file:

```python
# autogenerate cannot manage CONCURRENTLY indexes
transactional_ddl = False
```

### Rename a column without locking

Three releases — an in-place rename takes `AccessExclusiveLock` and stalls
every reader on a populated table:

1. Add the new column, dual-write at the app level, backfill.
2. Switch reads to the new column.
3. Drop the old column.

### Drop a column

Two releases, to avoid "ghost reads" during a rolling deploy:

1. Remove all reads and writes from app code. Deploy.
2. Drop the column in a migration.

### Data migration

Its own revision, separate from any DDL:

```python
def upgrade():
    op.get_bind().execute(text("""
        UPDATE seed_detections
        SET confidence = 0
        WHERE confidence IS NULL
    """))
```

Bulk DML on a large table: chunk it. A single table-wide `UPDATE` holds locks
for the whole statement and can block writers for the duration.

## Replication / CDC implications

If the migration touches a table published for ClickHouse CDC:

1. Add a new table to the publication in a `transactional_ddl = False`
   revision: `ALTER PUBLICATION seedbank_pub ADD TABLE widgets;`.
2. Add the matching `dim_*` / `fact_*` schema under the ClickHouse migrations.
3. Update the CDC worker mapping (table → ClickHouse insert shape) in
   `workers/tasks/dwh.py`.
4. Add an integration test asserting a Postgres write lands in ClickHouse.

## Gotchas

- A green `alembic upgrade head` on an empty dev DB proves nothing about a
  populated one. Always run step 6 for anything touching existing rows.
- `alembic stamp head` marks revisions applied **without running them** — only
  for recovering a drifted history, never as a shortcut past a failing upgrade.
- Never edit a migration that has already been applied anywhere shared. Add a
  new revision instead; history is append-only once it has left your machine.

## Checklist

- [ ] Forward and backward both run cleanly on an empty DB
- [ ] Forward and backward both run cleanly on a seeded DB
- [ ] All FKs have a supporting index
- [ ] All `type` / `status` string columns have a CHECK or are real ENUMs
- [ ] Timestamps are TZ-aware
- [ ] `CONCURRENTLY` used for indexes on large tables
- [ ] Any data migration is in its own revision
- [ ] Publication / DWH updated if the table is CDC-published
- [ ] App code runs against both old and new schema during the deploy window

## Useful commands

```bash
alembic current
alembic history --verbose
alembic show <rev>
alembic upgrade +1     # one step forward
alembic downgrade -1   # one step back
alembic stamp head     # mark applied without running (recovery only)
```
