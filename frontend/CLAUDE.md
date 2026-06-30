# Frontend — Claude Guide (`frontend/`)

Loaded on demand when you work under `frontend/`. It does not repeat the root
`CLAUDE.md` (read that for the four surfaces, the workflow, and the backend
contract) — this file covers only the web client's stack, layout, conventions,
gotchas, and gates.

---

## Stack

- **React 18.3 + TypeScript 5.6 strict** — `noUnusedLocals`,
  `noUnusedParameters`, `noUncheckedIndexedAccess` are on, so index access is
  `T | undefined` and unused symbols fail the build. Treat them as guardrails,
  not nags.
- **Vite 5.4** (dev server on `:5173`). Package manager is **npm**
  (`package-lock.json`). Path alias `@/*` → `./src/*`.
- **Tailwind 3.4 + shadcn/ui (Radix)**. Theme tokens are CSS variables in
  `src/styles/globals.css`; dark mode via the `class` strategy. No hardcoded
  colors — use the Tailwind tokens so dark mode and theming keep working.
- **React Router v6** with `React.lazy` route splitting (`src/router.tsx`).
- **TanStack Query v5** for server state; React Context only for auth, i18n,
  theme. Provider order in `src/main.tsx` is fixed:
  `I18nProvider → ThemeProvider → QueryClientProvider → AuthProvider →
  RouterProvider`.

---

## API client (`src/lib/api/`)

Typed via **openapi-fetch** over a generated schema.

- `schema.d.ts` is **generated** by `npm run gen:api` (openapi-typescript) —
  never hand-edit it. Regenerate when the backend contract changes.
- `client.ts` — `authMiddleware` attaches the token; `refreshTokens` dedupes
  concurrent 401 retries so a token expiry doesn't fan out into N refreshes.
- `errors.ts` — maps RFC 9457 `problem+json` into `ApiError`.
- `types.ts` — ergonomic aliases over the generated types.

Always call `unwrap<T>(result)` inside query/mutation fns — it throws `ApiError`
on `!ok` and peels the backend `Envelope`/`Page` wrapper so components get the
payload, not the envelope. `VITE_API_BASE_URL` is the **origin only** (no
`/api/v1` — the generated paths already include it).

---

## Auth

Access token lives in memory (`lib/auth/token-store.ts`); refresh token in
`localStorage`. `ensureAccessToken()` runs at boot; a 401 triggers
`refreshTokens()` (deduped) then retries the request. Roles are
`end_user / ai_developer / admin`. Route guards live in
`components/guards/{protected-route,role-route}.tsx`; gate on `hasRole(user,
allowed)`.

---

## Forms

React Hook Form + Zod via `@hookform/resolvers`. On submit, call
`applyApiError(err, form.setError)` from `lib/form.ts`: 422 field errors map
onto the matching fields; everything else surfaces as a `sonner` toast. This
keeps validation feedback inline and unexpected failures visible.

---

## i18n / RTL

Custom, no heavy library. `src/i18n/dictionaries/en.ts` is the **source of
truth** (the `TranslationKey` master union + `enPlurals`); `ar.ts` must mirror
its keys exactly. Use `t()` / `tn()` from `useI18n()`. `dir` from `useI18n()`
drives layout — write **logical CSS** (`inline-start`/`inline-end`, not
`left`/`right`) so RTL is free. Locale-aware formatters live in
`src/lib/format.ts`. No hardcoded user-facing strings — everything goes through
the dictionaries.

---

## Layout

Feature modules under `src/features/<name>/`:

- `api.ts` — a `<name>Keys` query-key factory + service fns + the `useQuery` /
  `useMutation` hooks, each `unwrap()`-ing its result.
- `pages/` — page components; `components/` — optional local UI.
- Register each page as a lazy route in `src/router.tsx` behind
  `ProtectedRoute` / `RoleRoute`.

Shared UI: `components/ui/` (shadcn primitives), `components/shared/`
(`bbox-overlay`, `confidence-badge`, `pagination`, `states`, `status-badge`,
…), `components/layout/` (`app-shell`, `sidebar`, `topbar`, `nav.ts`). Existing
feature modules: analytics, analyze, auth, batches, catalog, compare,
dashboard, datasets, experiments, models, profile, users.

---

## Gates (`package.json` scripts)

| Script | What it runs |
|---|---|
| `npm run lint` | ESLint 9 flat config + typescript-eslint + jsx-a11y + react-hooks |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run test` | Vitest (jsdom) + `@testing-library/react`, setup `src/test/setup.ts` |
| `npm run format` | Prettier — 90 width, double quotes, trailing commas |
| `npm run build` | `tsc && vite build` |
| `npm run gen:api` | regenerate `src/lib/api/schema.d.ts` from the backend OpenAPI |

`consistent-type-imports` is enforced — use inline `import { type Foo }`. When
the backend contract drifts, reconcile with the **`api-contract`** skill.

---

## Gotchas

- Editing `schema.d.ts` by hand — it's regenerated; your change disappears.
  Run `gen:api` against the live backend instead.
- Forgetting `unwrap()` — you'll leak the `Envelope`/`Page` shape into
  components and the types won't match.
- Physical CSS (`left`/`right`, `ml-`/`mr-`) breaks Arabic/RTL — use logical
  properties.
- Putting `VITE_API_BASE_URL` with `/api/v1` doubles the prefix; origin only.
