---
name: mobile-dev
description: Recipe for adding or changing a screen in the seed-bank Expo / React Native app (mobile/). Use when you create a new screen, add a route, wire a TanStack Query call, add EN/AR strings, or theme a component. Covers the web-vs-native FormData trap, the localhost→LAN-IP device gotcha, Hermes i18n limits, and api/types.ts drift.
---

## Purpose

Add a screen to the Expo app (`mobile/`) without breaking the contracts the
app relies on: typed navigation, async-aware data fetching, bilingual strings,
and palette-aware UI. The recipe keeps a new screen consistent with the six
that already exist so a second dev can follow the same shape.

## When to use

- Adding a new screen or modal route.
- Wiring a screen to a backend endpoint with `useQuery`/`useMutation`.
- Adding user-facing copy (every string is EN + AR).
- Reviewing a screen PR for the conventions below.

Stack reference: Expo SDK 56, RN 0.85, React 19, TypeScript strict,
`@react-navigation` 7, TanStack Query v5. Module alias `@` → `mobile/src`.

## Steps

Add-a-screen, in order:

1. **Create the screen** under `src/screens/<name>-screen.tsx`. Export a named
   component. Build it from `src/components/ui.tsx` primitives and theme palette
   colors — see `home-screen.tsx` for the layout shape.
2. **Add a typed route.** Declare params in `src/navigation/types.ts`
   (`RootStackParamList` for stack/modal routes, `TabsParamList` for tabs;
   `undefined` when the screen takes none), then register the `<Stack.Screen>`
   or `<Tab.Screen>` in `src/navigation/root-navigator.tsx`. Typing the param
   list is what makes `navigation.navigate(...)` and the route prop checked.
3. **Wire data with TanStack Query.** Reads use `useQuery` against a function in
   `src/api/` (e.g. `getBatch` in `batches.ts`); writes use `useMutation`. Never
   call `fetch` from a screen — go through `apiData`/`apiFetch` in
   `src/api/client.ts` so bearer auth and 401-refresh apply. For an async
   resource (analyze → batch), set `refetchInterval` and stop polling once
   `isTerminal(status)`, then render the result.
4. **Add EN + AR strings.** Put the copy in `src/i18n/dictionaries/en.ts` and
   `ar.ts` (plurals in the `*Plurals` maps), and read it via `useI18n()` →
   `t(key)` / `tn(key, count)`. A key missing from `ar.ts` is a type error in
   strict mode — so both dictionaries stay in lockstep.
5. **Theme + primitives.** Use `useTheme()` for the palette and the `ui.tsx`
   primitives (Loader, Card, AppButton, TextField, StatusPill, H1, Muted)
   rather than ad-hoc `StyleSheet` colors — they already handle dark mode and
   RTL.
6. **Verify:** from `mobile/`, run `npm run typecheck` (`tsc --noEmit`). There
   is no test runner yet, so strict TS is the gate.

## Conventions

- One screen per file, named `<name>-screen.tsx`, named export.
- Screens read data through `src/api/*` functions, never raw `fetch`.
- All copy is keyed and bilingual; no hardcoded display strings.
- Colors and spacing come from the theme + `ui.tsx`, not inline hex.
- Route params are typed in `navigation/types.ts` before use.

## Gotchas

- **Web vs native FormData.** On web, resolve the URI to a `Blob` and append a
  `File` — branch on `Platform.OS`, as `toUploadPart` in `src/api/batches.ts`
  does. The RN `{ uri, name, type }` descriptor 422s on web (bug #45); see
  [Expo Web FormData](../../memory/known-issues.md#expo-web-formdata-needs-a-real-blob-or-file).
- **localhost → LAN IP on a real device.** `app.json` defaults `apiBaseUrl` to
  `http://localhost:8000`, which a phone can't reach. Override the base URL at
  runtime via the Settings screen / `src/api/config.ts` (persisted to
  AsyncStorage) to your dev machine's LAN IP.
- **No `Intl` in i18n.** Hermes ships a partial `Intl` — `Intl.PluralRules` is
  unreliable for Arabic and date formatting via `Intl` is avoided. Use `tn` and
  the hand-rolled CLDR plurals in `src/i18n/translate.ts`.
- **`src/api/types.ts` drifts.** Hand-written subset, not generated — reconcile
  against the backend via the `api-contract` skill before relying on it; see
  [API types drift](../../memory/known-issues.md#mobile-and-fe-api-types-drift).

## Checklist

- [ ] Screen built from `ui.tsx` primitives + theme palette, no inline colors.
- [ ] Route + params typed in `navigation/types.ts`; registered in `root-navigator.tsx`.
- [ ] Data via `useQuery`/`useMutation` through `src/api/*` (no raw `fetch`).
- [ ] Async results poll until `isTerminal(status)` before rendering.
- [ ] New copy added to both `en.ts` and `ar.ts`; read via `t`/`tn`.
- [ ] Any upload branches web vs native for FormData.
- [ ] `npm run typecheck` passes.
