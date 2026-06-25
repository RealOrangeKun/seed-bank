# Seed Bank — Mobile

A React Native (Expo) app that lets farmers check seed quality from their phone:
point the camera at seeds, capture, and get an instant good/bad breakdown powered
by the same Seed-Bank backend the web app uses.

Built for the field: **bilingual (English + العربية) with full RTL**, a calm
agricultural-green theme, light/dark modes, and a one-tap realtime camera flow.

## Features

- **Realtime camera capture** (`expo-camera`) — live preview with a framing
  guide, multi-shot capture, a thumbnail strip, and one-tap upload for analysis.
- **Result polling** — the result screen polls the batch until analysis finishes,
  then shows the good-rate, seed counts, and mean confidence.
- **Scan history** with pull-to-refresh.
- **Localization** — English / Arabic with automatic **RTL** layout mirroring
  (via `I18nManager`); the choice persists and survives restarts. CLDR plural
  rules are implemented by hand (Hermes ships only a partial `Intl`).
- **Secure auth** — tokens in the OS keystore (`expo-secure-store`) with a
  transparent refresh-on-401, mirroring the web client.
- **Configurable server** — set the API base URL from Settings (handy for testing
  against a dev machine's LAN IP, since `localhost` on a phone is the phone).

## Architecture

```
src/
  api/          fetch client (auth + refresh), auth, batches/analyze, tokens, config
  auth/         session context (loading → authenticated → unauthenticated)
  components/   themed UI primitives (Button, Card, TextField, StatusPill, …)
  i18n/         en/ar dictionaries, hand-rolled plural rules, RTL-aware provider
  navigation/   bottom tabs (Capture / History / Settings) + root stack (Result)
  screens/      login, camera, result, history, settings
  theme/        agricultural-green palette (light/dark) + theme context
```

The API layer intentionally mirrors the web client's contract: `{ data }`
envelopes, the `/api/v1/...` paths, multipart upload to `POST /api/v1/analyze`,
and bearer auth with a single refresh-and-retry on `401`.

## Running

Requires the Seed-Bank backend running and reachable from your device/emulator.

```bash
cd mobile
npm install
npm start            # then press a / i, or scan the QR with Expo Go
```

Set the API address: either edit `app.json` → `expo.extra.apiBaseUrl`, or open
the app and set **Settings → Server address** (e.g. `http://192.168.1.10:8000`).
On a physical phone, `localhost` points at the phone — use your machine's LAN IP.

## Notes

- Switching language to/from Arabic flips the layout direction, which React
  Native applies on the **next app launch** — the app triggers a reload
  (`expo-updates`) automatically in production builds.
- Camera capture requires a physical device or an emulator with a virtual camera;
  the iOS Simulator has no camera.
