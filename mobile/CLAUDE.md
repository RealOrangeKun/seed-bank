# Mobile — Claude Guide (`mobile/`)

Loaded on demand when you work under `mobile/`. It does not repeat the root
`CLAUDE.md` (read that for the four surfaces, the workflow, and the backend
contract) — this file covers only the mobile client's stack, layout,
conventions, gotchas, and gates.

---

## Stack

- **Expo SDK 56 / React Native 0.85 / React 19.** `react-native-web 0.21`
  gives an Expo Web target, so the same screens run in a browser — which is why
  several modules branch on `Platform.OS`.
- **TypeScript strict.** Module alias `@` → `./src` via babel-module-resolver.
- **`app.json`** — `apiBaseUrl` defaults to `http://localhost:8000`;
  `newArchEnabled` is on.

---

## Navigation

`@react-navigation` v7 (native-stack + bottom-tabs).
`src/navigation/root-navigator.tsx`:
`Splash` (loading) → `Login` (unauthenticated) → `Tabs`
(Home, Capture, History, Settings). `Result` is a modal. Route params are typed
in `src/navigation/types.ts` — keep that union in step with the screens.

---

## Data + API (`src/api/`)

TanStack Query v5 for server state.

- `client.ts` — bearer auth + transparent 401 refresh + multipart upload.
- `tokens.ts` — `expo-secure-store` on native, `localStorage` on web;
  access token kept in memory and loaded at startup.
- `batches.ts` — `analyzePhotos` (multipart upload), `listBatches`, `getBatch`,
  `tallyBatch`, `isTerminal`.
- `config.ts` — runtime base-URL override persisted to `AsyncStorage`, so you
  can point the app at a dev machine's LAN IP without rebuilding.
- `types.ts` — a **hand-written** subset of the backend contract (`TokenPair`,
  `MeOut`, `BatchOut`/`DetailOut`, `Envelope<T>`, `Page<T>`, …). It **drifts**
  from the backend; when an endpoint shape changes, reconcile it with the
  **`api-contract`** skill rather than guessing.

---

## Camera upload gotcha (was bug #45 — a 422)

On **web** you must append a real `Blob`/`File` to `FormData`. The React Native
`{ uri, name, type }` descriptor stringifies to `"[object Object]"` in a
browser, so the upload fails validation. `Platform.OS` branches in
`batches.ts` and `tokens.ts` handle this — keep those branches when you touch
upload code.

---

## Result flow

`screens/result-screen.tsx` polls with `refetchInterval` (~2s) until the batch
status `isTerminal`, then renders the tally (good-rate %, counts, confidence).
Analysis is async on the backend, so the screen must tolerate a pending batch.

---

## i18n / theme

- **Hermes-safe i18n.** No `Intl.PluralRules` (Hermes lacks it) — plurals are
  hand-rolled CLDR rules in `translate.ts`, and `formatDateTime` avoids `Intl`.
  Dictionaries `en.ts` / `ar.ts`; use `t()` / `tn()`. `I18nManager` drives RTL
  and the app reloads on locale change.
- **Theme.** `src/theme/colors.ts` (light/dark palettes); `use-theme.tsx`
  resolves system/light/dark and persists the choice. UI primitives in
  `components/ui.tsx` (`Loader`, `Card`, `AppButton`, `TextField`,
  `StatusPill`, `H1`, `Muted`) are palette-aware — build screens from them, not
  ad-hoc `StyleSheet` colors, so dark mode stays consistent.

---

## Gates (`package.json` scripts)

| Script | What it runs |
|---|---|
| `npm start` | Expo dev server |
| `npm run android` / `npm run ios` | platform launchers |
| `npm run typecheck` | `tsc` |

No web/build script and no tests yet — `typecheck` is the only automated gate.

---

## Gotchas

- On a real device, `localhost` points at the phone. Override the server URL to
  the dev machine's LAN IP from the Settings screen (`api/config.ts`).
- Reaching for `Intl` (`PluralRules`, `DateTimeFormat`) crashes or misbehaves
  on Hermes — use the hand-rolled helpers in `translate.ts`.
- Editing `api/types.ts` to match a hunch — confirm against the real backend
  contract via the `api-contract` skill; it is a manual subset that drifts.
- Bypassing `components/ui.tsx` primitives breaks theming and RTL.
