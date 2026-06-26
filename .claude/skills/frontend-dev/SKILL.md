---
name: frontend-dev
description: Frontend conventions and the add-a-feature-module recipe for the seed-bank React SPA (frontend/) — typed openapi-fetch client + unwrap(), TanStack Query key factories, RHF+Zod forms, i18n/RTL, lazy guarded routes, and the lint/typecheck/test gates. Use whenever you write or modify code under frontend/src/.
---

# Frontend dev — seed-bank SPA conventions

This skill is the recipe for building UI in `frontend/`. Read it before you
touch `frontend/src/`. The `frontend-engineer` subagent reviews against the
same rules, so following this is also how you pass review.

Stack: React 18.3 + TypeScript 5.6 (strict, `noUncheckedIndexedAccess`), Vite,
Tailwind 3.4 + shadcn/ui, React Router v6 (lazy routes), TanStack Query v5, a
typed `openapi-fetch` client generated from the backend OpenAPI, React Hook Form
+ Zod, and a custom i18n/RTL layer. Path alias `@/*` → `./src/*`.

## Purpose

Add a feature to the SPA the way the rest of the app is built: a self-contained
feature module that fetches through the typed client, renders behind the right
route guard, and ships translated, RTL-safe, accessible UI. Following the recipe
keeps caching, error handling, and i18n uniform across every screen — so a bug
fixed in one place is fixed everywhere.

## When to use

- Adding a new page or screen (a list, a detail view, a form).
- Adding a new server call (query or mutation) for an existing feature.
- Wiring a new route, or moving a surface behind a different guard.
- Reviewing your own UI diff before handing it to `frontend-engineer`.

If you only need backend work, use `backend-dev` / `add-endpoint` instead.

## Steps

The running example is a feature called `widgets`.

### 1. Create the feature module

```
src/features/widgets/
  api.ts        # query-key factory + service fns + hooks (each unwrap()-ing)
  pages/        # page components (the route targets)
  components/   # optional: UI used only by this feature
```

Truly shared UI (badges, pagination, state placeholders) already lives in
`src/components/shared` and `src/components/ui` — import it, don't re-create it.

### 2. Write `api.ts`

Three parts, in this order: a key factory, service functions that call the typed
client and `unwrap()`, then the hooks.

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";
import type { Envelope, Page, WidgetOut } from "@/lib/api/types";

export interface WidgetListParams {
  page: number;
  pageSize: number;
}

// Query-key factory — the single source of truth for this feature's cache keys.
export const widgetKeys = {
  all: ["widgets"] as const,
  list: (params: WidgetListParams) => [...widgetKeys.all, "list", params] as const,
  detail: (id: string) => [...widgetKeys.all, "detail", id] as const,
};

async function listWidgets(params: WidgetListParams): Promise<Page<WidgetOut>> {
  const result = await api.GET("/api/v1/widgets", {
    params: { query: { page: params.page, page_size: params.pageSize } },
  });
  return unwrap<Page<WidgetOut>>(result); // Page<T> keeps { data, meta }
}

async function getWidget(id: string): Promise<WidgetOut> {
  const result = await api.GET("/api/v1/widgets/{widget_id}", {
    params: { path: { widget_id: id } },
  });
  const env = await unwrap<Envelope<WidgetOut>>(result);
  return env.data; // Envelope<T> → unwrap the .data
}

export function useWidgets(params: WidgetListParams) {
  return useQuery({
    queryKey: widgetKeys.list(params),
    queryFn: () => listWidgets(params),
  });
}

export function useCreateWidget() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createWidget,
    onSuccess: () => void qc.invalidateQueries({ queryKey: widgetKeys.all }),
  });
}
```

Every service fn ends in `unwrap<T>(result)` — it throws `ApiError` on `!ok`,
so a failed request becomes a typed error your hooks and forms already know how
to surface. Reads of `Envelope<T>` take `.data`; `Page<T>` keeps `data` + `meta`
for pagination.

### 3. Register a lazy, guarded route

In `src/router.tsx`, mount the page with `React.lazy` and wrap it in the right
guard:

```tsx
const WidgetsPage = lazy(() => import("@/features/widgets/pages/widgets-page"));

// ...inside the route tree:
{
  path: "widgets",
  element: (
    <ProtectedRoute>
      <WidgetsPage />
    </ProtectedRoute>
  ),
}
```

Use `ProtectedRoute` for any authenticated page. For `ai_developer`/`admin`-only
surfaces use `RoleRoute` with an `allowed` role list (`src/components/guards/`).
An authenticated page with no guard is a security bug, not a nit.

### 4. Add strings to `en.ts`, then mirror in `ar.ts`

`src/i18n/dictionaries/en.ts` is the source of truth — its keys define the
`TranslationKey` union. Add your keys there first, then copy the **same** keys
into `ar.ts` with Arabic values. Render them via `t()` / `tn()` from
`useI18n()`; never inline a literal user string.

```tsx
const { t, dir } = useI18n();
return <h1>{t("widgets.title")}</h1>;
```

A key in `en.ts` missing from `ar.ts` ships an untranslated UI to RTL users —
treat it as broken.

### 5. Build the form (RHF + Zod + `applyApiError`)

```tsx
const form = useForm<WidgetForm>({ resolver: zodResolver(widgetSchema) });
const { mutateAsync } = useCreateWidget();

const onSubmit = form.handleSubmit(async (values) => {
  try {
    await mutateAsync(values);
  } catch (err) {
    applyApiError(err, form.setError); // 422 → fields, else toast
  }
});
```

`applyApiError` (`@/lib/form.ts`) maps RFC 9457 field errors onto the matching
inputs and toasts everything else via sonner — so every form fails the same way.
Don't hand-roll per-form error handling.

### 6. Verify the gates

From `frontend/`:

```bash
npm run lint && npm run typecheck && npm run test
```

`lint` is ESLint flat config (typescript-eslint + jsx-a11y + react-hooks);
`typecheck` is `tsc --noEmit`; `test` is `vitest run` (jsdom +
@testing-library/react). Fix all three before handing off.

## Conventions

- **Logical CSS for RTL.** Use `inline-start`/`inline-end`, `ps-*`/`pe-*`,
  `text-start` — never physical `left`/`right`/`ml-*`/`mr-*`. `dir` from
  `useI18n()` flips logical properties; physical ones don't, and the Arabic
  layout breaks. Format dates/numbers via `src/lib/format.ts` so they follow the
  active locale.
- **No hardcoded tokens.** Colors come from CSS variables / Tailwind theme
  tokens (`src/styles/globals.css`), strings from i18n, the API base from env.
  A hardcoded hex breaks dark mode; a hardcoded string breaks i18n.
- **Inline `import type`.** `consistent-type-imports` is enforced — write
  `import type { WidgetOut } from "..."`, mixing types into a value import fails
  lint.
- **Strict index access.** `noUncheckedIndexedAccess` makes `arr[i]` a
  `T | undefined`; narrow it (guard, `?.`, default) rather than asserting.
- **Provider order is fixed** (`src/main.tsx`): I18nProvider → ThemeProvider →
  QueryClientProvider → AuthProvider → RouterProvider. Don't reorder; auth and
  data both assume i18n/theme are already mounted.

## Gotchas

- **`VITE_API_BASE_URL` is the origin only** — no `/api/v1`. The generated
  client paths already carry the prefix; adding it again makes every request
  404.
- **`src/lib/api/schema.d.ts` is generated** by `npm run gen:api` from
  `openapi.json`. Never hand-edit it. A wrong type means the schema is stale —
  regenerate after the backend contract changes (the full FE+mobile sync flow is
  the `api-contract` skill; see [API types drift](../../memory/known-issues.md#mobile-and-fe-api-types-drift)).
- **Don't skip `unwrap()`.** A query fn that returns the raw `openapi-fetch`
  result hands callers `{ data, error, response }`, not your data, and silently
  swallows API errors — they never reach `applyApiError` or an error boundary.
- **Inline query-key arrays drift.** Always read keys from the feature's
  `<name>Keys` factory so a list hook and the mutation that invalidates it agree
  on the exact key.
- **`build` runs the typechecker** (`tsc --noEmit && vite build`), so a type
  error fails the build, not just `typecheck`. Keep types green as you go.

## Checklist

- [ ] Feature module under `src/features/<name>/` (`api.ts`, `pages/`, optional `components/`)
- [ ] `api.ts` exports a `<name>Keys` factory; every service fn ends in `unwrap<T>()`
- [ ] `Envelope<T>` unwrapped to `.data`; `Page<T>` keeps `data` + `meta`
- [ ] Mutations invalidate via the key factory
- [ ] Page mounted as a `React.lazy` route in `src/router.tsx` behind `ProtectedRoute`/`RoleRoute`
- [ ] Every user string via `t()` / `tn()`; keys added to `en.ts` and mirrored in `ar.ts`
- [ ] Logical CSS only (no physical `left`/`right`/`ml-*`/`mr-*`); dates/numbers via `format.ts`
- [ ] No hardcoded colors, strings, or URLs
- [ ] Forms use RHF + Zod + `applyApiError(err, form.setError)`
- [ ] a11y clean (labels, accessible names, keyboard reachable)
- [ ] `npm run lint && npm run typecheck && npm run test` all green
