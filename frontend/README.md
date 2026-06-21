# Seed-Bank Frontend

A production-grade React SPA for the Seed-Bank API: upload seed images for
detection + quality classification, review results with bounding-box overlays,
and operate the ML platform (model registry, datasets, experiments, A/B traffic)
and admin (users) — all gated by role.

> Replaces the archived vanilla-JS prototype in `legacy/frontend/` (not reused).

## Stack

- **React 18 + TypeScript (strict)** on **Vite**
- **Tailwind CSS + shadcn/ui** (Radix) — agricultural-green theme via CSS-variable design tokens, light/dark
- **TanStack Query** for server state (caching, polling, retries)
- **React Router v6** with role-aware guards and route-level code splitting
- **React Hook Form + Zod** for forms (constraints mirror the backend schemas)
- **openapi-fetch + openapi-typescript** — the client is typed against the API's
  OpenAPI contract; types are generated, not hand-written
- **Vitest + Testing Library** for unit tests; **ESLint + Prettier**

## Architecture

Feature-based, layered to mirror the backend's discipline:

```
src/
  lib/            api client (auth + refresh-on-401 + RFC 9457 errors), env, query client, formatters
  lib/api/        generated schema.d.ts + ergonomic type aliases
  components/ui/  shadcn primitives          components/shared/  cross-feature widgets (bbox overlay, dropzone, …)
  components/layout/  app shell, sidebar, topbar    components/guards/  ProtectedRoute, RoleRoute
  features/<name>/  api.ts (query/mutation hooks) + pages/  — one folder per feature
  router.tsx      route tree with guards + lazy pages
```

Conventions: every request/response flows through the typed client and is
unwrapped from its `{data}` / `{data, meta}` envelope; API decimals
(`confidence`, bbox coords) stay strings and are parsed only at render to
preserve precision; all config comes from `VITE_*` env (no hardcoded URLs).

## Getting started

```bash
cp .env.example .env          # set VITE_API_BASE_URL (the API *origin*, e.g. http://localhost:8000)
npm install
npm run dev                   # Vite on http://localhost:5173
```

The API must allow the dev origin via `CORS_ALLOW_ORIGINS` (the repo's `.env`
already includes `http://localhost:5173`). Bring the backend up with `make up`
from the repo root.

### Scripts

| Script | What it does |
|---|---|
| `npm run dev` | Dev server (port 5173) |
| `npm run build` | Type-check + production build |
| `npm run preview` | Serve the production build |
| `npm run lint` | ESLint | 
| `npm run typecheck` | `tsc --noEmit` |
| `npm run test` | Vitest |
| `npm run gen:api` | Regenerate `src/lib/api/schema.d.ts` from `openapi.json` |

### Regenerating API types

`openapi.json` is the API's OpenAPI spec. Refresh it from the running app, then
regenerate the TypeScript types:

```bash
# from the repo root (the app builds the spec without external services):
python -c "import json; from seedbank.main import create_app; \
  open('frontend/openapi.json','w').write(json.dumps(create_app().openapi(), indent=2))"
# then:
cd frontend && npm run gen:api
```

The strict compiler then flags any place the frontend drifts from the contract.

## Auth

Email/password login, register (with email verification), and refresh-token
rotation. The access token is held in memory; the refresh token in
`localStorage` recovers the session on reload (the API returns tokens in the
body, not httpOnly cookies). Roles: `end_user`, `ai_developer`, `admin`
(admin ⊇ all) — the sidebar and routes hide what a role can't use.

OAuth (Google/GitHub) buttons are intentionally **not** wired: the backend's
OAuth callback returns token JSON to the browser, which a SPA can't capture
without a small backend redirect change (out of scope here).

## Docker

```bash
# from the repo root — opt-in `frontend` compose profile (nginx on :5173):
make up-front
```

The image is a multi-stage build (Node build → nginx static serve).
`VITE_API_BASE_URL` is a **build arg** because Vite inlines env at build time.

## Known API gaps (surfaced in the UI)

- No `seed-types` or `suppliers` listing endpoint exists, so those IDs are shown
  as short UUIDs and entered as optional UUID fields (analyze, traffic).
- Images are fetched via the presigned-URL endpoint added for this UI:
  `GET /api/v1/batches/{id}/image-urls`.
