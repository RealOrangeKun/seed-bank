---
name: api-contract
description: Keep the frontend and mobile clients in sync with the backend OpenAPI contract after a Pydantic schema change. Use whenever you add, rename, or remove a field on a request/response schema, change a DomainError code, or alter the Envelope/Page shape — anything a client consumes.
---

# Sync the API contract across surfaces

## Purpose

The backend is the single source of truth for the API contract. Two clients
consume it differently: the **frontend** regenerates a typed schema from the
OpenAPI spec, so a backend change surfaces as a TypeScript error you can chase
down. The **mobile** app hand-writes a subset of the contract in
`mobile/src/api/types.ts`, so a backend change surfaces as *nothing* — it
drifts silently until a request 422s in someone's hands. This skill makes both
clients catch up deliberately, in one pass, right after the schema change.

## When to use

After any change to a Pydantic schema in `src/seedbank/schemas/` that a client
reads or sends. Concretely: a new field, a renamed or removed field, a changed
type or nullability, a new `DomainError` code, or a change to the `Envelope[T]`
/ `Page[T]` wrapper. If the change is purely internal (a service signature, a
repo, an ORM column with no schema exposure), no client work is needed.

## Steps

### 1. Backend — produce the current OpenAPI spec

The app serves the live spec at `GET /api/v1/openapi.json` (`openapi_url` is set
from `settings.api_v1_prefix` in `src/seedbank/main.py`). You need that JSON on
disk so the frontend codegen can read it.

- **Against a running server** (e.g. `make up` is healthy):

  ```bash
  curl -s http://localhost:8000/api/v1/openapi.json -o frontend/openapi.json
  ```

- **Offline, no server** — render it from the app factory. `create_app()` builds
  the FastAPI instance and `app.openapi()` returns the spec dict, so nothing has
  to be listening on a port:

  ```bash
  python -c "import json; from seedbank.main import create_app; \
    print(json.dumps(create_app().openapi()))" > frontend/openapi.json
  ```

`frontend/openapi.json` is the input the codegen reads — keep this dump and the
backend in lockstep. A stale dump regenerates stale types that compile cleanly
and lie at runtime.

### 2. Frontend — regenerate and let the compiler find the breaks

```bash
cd frontend
npm run gen:api    # openapi-typescript ./openapi.json -> src/lib/api/schema.d.ts
npm run typecheck  # tsc --noEmit — this is where renames/removals light up
```

`gen:api` rewrites `src/lib/api/schema.d.ts` from `openapi.json`. Then
`typecheck` is the actual signal: a removed or renamed field breaks every
`unwrap<T>()` call site and feature `api.ts` that referenced it. Walk the errors
and fix the call sites — that is the point of the typed client, so don't paper
over them with `any`.

### 3. Mobile — reconcile the hand-written subset

Mobile has **no** codegen. `mobile/src/api/types.ts` is a hand-maintained subset
of the backend contract (`TokenPair`, `MeOut`, `BatchOut`/`BatchDetailOut`,
`Envelope<T>`, `Page<T>`, the detection/inference shapes, …). Open the changed
backend schema side by side with this file and bring the affected types into
agreement by hand:

- Field added that mobile uses → add it (match optionality and type).
- Field renamed/removed → rename/remove it, then fix the screens/`api/*.ts`
  that read it.
- Type or nullability changed → mirror it (e.g. `confidence` is a
  `NUMERIC(5,4)` that serializes as a string — mobile types it
  `string | number`).
- Enum value added/removed (e.g. a new `BatchStatus`) → update the union and
  any `isTerminal`-style switch that branches on it.

`mobile` has no `typecheck` in CI by default, but you can run it locally:

```bash
cd mobile
npm run typecheck   # tsc — catches references you missed after editing types.ts
```

### 4. Flag breaking changes explicitly

Some changes break a client even when both compile. Call these out in the PR
description so the other dev (and the release) is not surprised:

- **Error `code` enum changes.** Clients branch on the RFC 9457 `code`
  (frontend `lib/api/errors.ts` → `ApiError`, mobile error handling). Renaming
  or removing a `DomainError` code silently breaks that branching.
- **Envelope/Page shape changes.** Every client unwraps `{data: ...}` (single)
  and `{data: [...], meta: {...}}` (paginated). Touching the wrapper touches
  every read path on both surfaces.
- **Field rename/removal.** Frontend catches it at `typecheck`; mobile does not
  — that asymmetry is exactly the #45 class of bug. Treat a rename as a
  removal-plus-addition and audit mobile by hand.

## Conventions

- `frontend/src/lib/api/schema.d.ts` is **generated** — never hand-edit it. Fix
  the spec and rerun `gen:api`; a manual edit is overwritten on the next run.
- `VITE_API_BASE_URL` is the **origin only** (no `/api/v1`). The generated paths
  already include the prefix, so the client `baseUrl` is `env.apiOrigin`. Don't
  add the prefix in two places.
- Keep `frontend/openapi.json` as the regeneration input. Commit it alongside
  the regenerated `schema.d.ts` so reviewers can diff the contract change.
- Mobile types intentionally cover only what the app uses. Don't mirror the
  whole spec into `types.ts` — extend the subset to match what changed.

## Gotchas

- **Mobile drifts silently.** No codegen, no automatic break. If you change a
  schema and skip step 3, the failure shows up as a runtime 422 on a real
  device, not a red build. This is bug #45's failure mode — budget the manual
  pass every time.
- **A stale `openapi.json` compiles fine and is wrong.** If you regen types from
  an old dump, `typecheck` passes against the old contract. Always redump
  (step 1) before `gen:api`.
- **`confidence` and normalized bboxes are strings on the wire.** Backend
  `NUMERIC` columns serialize as JSON strings; client types reflect that
  (`string | number`). Don't "fix" them to `number` in the schema.

## Checklist

- [ ] Backend: dumped the current spec to `frontend/openapi.json` (curl a
      running server, or `create_app().openapi()` offline).
- [ ] Frontend: ran `npm run gen:api`, then `npm run typecheck` clean; fixed
      every call site the rename/removal broke (no `any` papering).
- [ ] Mobile: reconciled `mobile/src/api/types.ts` by hand against the changed
      schema; ran `npm run typecheck` and fixed referencing screens/`api/*.ts`.
- [ ] Breaking changes (error `code`, Envelope/Page shape, field rename/removal)
      called out in the PR description.
- [ ] Committed the regenerated `schema.d.ts` and updated `openapi.json`
      together.
