# Known issues

Traps that have bitten — gotchas, environment quirks, and bugs with a known cause
and workaround. Each section is a stable anchor that skills and agents link to.
Indexed from [`MEMORY.md`](MEMORY.md).

_Last updated: 2026-06-30_

## Analyze needs a promoted detection model

`POST /analyze` can't run until at least one **detection** model is promoted to
`production` (and, for quality, a classifier per seed type). With none, the
model resolver (`services/model_resolver.py`) has nothing to resolve and the
batch goes `failed` with
`ModelNotReadyError: No production model …`. Production weights are gitignored
(MinIO is the source of truth), so a fresh stack and CI start with **zero**
models.

**Why it bites:** the mobile point-and-shoot flow sends no seed type, so it hits
the seed-type-agnostic fallback first — and the "register models" wording in
older `make seed`/smoke notes was aspirational; `seed_dev.py` never registered a
model.

- **Local/CI fix:** `make provision-smoke-model`
  (`scripts/provision_smoke_model.py`) builds a tiny seeded-random detector
  (`tiny-detector-smoke-v1`, no torch.hub download), uploads it to MinIO,
  registers it, and promotes staging→production. It runs in **worker-inference**
  (the api image has no torch — see [Lean
  Compose](decisions.md#lean-compose-without-degrading-quality)) with the seeded
  admin as actor (the `model_artifacts.created_by` FK needs a real user, not a
  random UUID).
- The `smoke.yml` workflow runs this between `make seed` and the smoke check.
- For a real model use `scripts/register_model.py` then promote via
  `PATCH /api/v1/models/{id}`.

## The 4 DWH tests xfail (#51)

The four `test_dwh_dualwrite` tests are **module-level xfail** (`strict=False`,
tracking issue `#51`). They pass in isolation but fail when run together.

**Why:** clickhouse-connect's async client is a thread-pool wrapper whose socket
binds to the event loop that created it. pytest-asyncio uses a fresh
per-function loop, so a reused client crosses loops →
`KeyError: <fileobj> is not registered`. Function-scoping the fixture and
resetting the cached client did not fix it — it's library-level. **The product
code is correct.** Don't "fix" the product code chasing these; confirm against
`#51` first, and if you touch DWH tests keep the xfail until it's resolved
(candidate fixes: a session-scoped loop, `clickhouse-connect[async]` prerelease,
or rearchitecting the client lifecycle). Related: [DWH
dual-write](decisions.md#dwh-is-app-level-dual-write-not-cdc),
[CI gates](workflow.md#ci-gates).

## Mobile and FE API types drift

The two clients track the backend contract differently, and one drifts:

- **Frontend** — `frontend/src/lib/api/schema.d.ts` is **generated** from the
  backend OpenAPI by `npm run gen:api`. Never hand-edit it; regenerate it.
- **Mobile** — `mobile/src/api/types.ts` is a **hand-written subset**
  (`TokenPair`, `MeOut`, `BatchOut`/`DetailOut`, `Envelope<T>`, `Page<T>`, …).
  It has no codegen, so it silently drifts from the real contract.

**Why it matters:** a backend schema change that isn't propagated leaves the
mobile types lying and the FE types stale — the class of bug behind contract
mismatches (see [Expo Web
FormData](#expo-web-formdata-needs-a-real-blob-or-file) for one that bit). After
any backend request/response schema change, run the **`api-contract` skill** — it
regenerates `schema.d.ts`, diffs and hand-reconciles `mobile/src/api/types.ts`,
and flags breaking changes (RFC 9457 `code` enums, `Envelope`/`Page` shape).
Don't edit `types.ts` to match a hunch.

## Expo Web FormData needs a real Blob or File

The mobile app runs on native **and** Expo Web (`react-native-web`). The React
Native multipart descriptor `{ uri, name, type }` works on native but
**stringifies to `"[object Object]"` in a browser**, so the upload fails backend
validation with a 422 (this was bug #45).

- On web you must append a real `Blob`/`File` to `FormData`; on native use the
  `{ uri, name, type }` descriptor. The `Platform.OS` branches in
  `mobile/src/api/batches.ts` (and `tokens.ts`) handle this — keep them when you
  touch upload or token code.
- Any new multipart upload path needs the same branch. Verify on **both**
  targets, not just native.
- Related: [Mobile and FE API types drift](#mobile-and-fe-api-types-drift).

## The api container does not migrate on boot

The `api` container does **not** run Alembic on startup. Only `make migrate`
(`alembic upgrade head` against the running api container) applies migrations.

**Why it bites:** after pulling a branch that adds a migration, the dev DB drifts
until you run it — and the failure is delayed and confusing. A real case: an
INSERT into `scan_batches` 500'd because the `share_token` column from migration
`0002` hadn't been applied yet. After `make up` on a fresh stack, and after
**any** pull that adds an `alembic/versions/` file, run `make migrate` once. CI
runs `make migrate` explicitly before smoke, so this is a local-dev trap, not a
CI one. See [`docs/operations.md`](../../docs/operations.md) and the
`db-migration` skill.

## `metadata` JSONB fields need explicit aliases

When a Pydantic `*Out` schema exposes a JSONB column as the field name
`metadata`, use an explicit pair: `validation_alias="<orm_attr>"` +
`serialization_alias="metadata"` (e.g. `SupplierOut` maps `supplier_metadata` →
`metadata`).

**Why:** do **not** reach for `AliasChoices("metadata", "supplier_metadata")`.
The `"metadata"` choice resolves against SQLAlchemy's `Base.metadata` attribute
on the ORM row, not the column, and 500s at serialization. Any new `*Out` field
literally named `metadata` (or shadowing another ORM/Base attribute) gets the
explicit `validation_alias` + `serialization_alias` treatment. Confirmed fix
shipped in the catalog endpoints; see
[`docs/adr/0001-frontend-backend-overhaul.md`](../../docs/adr/0001-frontend-backend-overhaul.md)
(P0 — the `SupplierOut` note).
