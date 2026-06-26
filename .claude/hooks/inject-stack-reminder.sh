#!/usr/bin/env bash
# UserPromptSubmit hook: inject a short, SURFACE-AWARE reminder when the prompt
# looks like implementation work. Cheap, non-blocking, fails open.
#
# This repo is a four-surface monorepo (backend / frontend / mobile / ML). The
# old version always injected the backend pillars; that was noise when working
# on the React or Expo apps. We now pick the reminder that matches the surface
# the prompt is about, and otherwise stay quiet.

set -euo pipefail

input="$(cat || true)"

prompt=""
if command -v jq >/dev/null 2>&1; then
  prompt="$(echo "$input" | jq -r '.prompt // empty' 2>/dev/null || true)"
fi

# Only react to prompts that smell like coding work — stay silent on Q&A.
if ! echo "${prompt}" | grep -Eiq '\b(implement|add|build|write|refactor|fix|create|scaffold|migrate|endpoint|router|service|repository|component|screen|migration|test)\b'; then
  exit 0
fi

emit() {
  # $1 = additionalContext string
  printf '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":%s}}\n' \
    "$(printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null || printf '"%s"' "$1")"
}

lc="$(printf '%s' "$prompt" | tr '[:upper:]' '[:lower:]')"

if echo "$lc" | grep -Eq '\b(frontend|react|vite|tailwind|tsx|jsx|shadcn|tanstack|i18n|rtl)\b'; then
  emit "Frontend reminder (frontend/): use the typed openapi-fetch client + unwrap() (never raw fetch; schema.d.ts is generated, don't hand-edit). Every user-facing string goes through t()/tn() — en.ts is the source of truth, mirror keys into ar.ts; use logical CSS for RTL. No hardcoded URLs/colors. Gates: npm run lint && npm run typecheck && npm run test. See frontend/CLAUDE.md and the frontend-dev skill."
elif echo "$lc" | grep -Eq '\b(mobile|expo|react native|react-native|screen|navigation|camera)\b'; then
  emit "Mobile reminder (mobile/): on web append a real Blob/File to FormData (the RN {uri,...} descriptor 422s on web — bug #45). Tokens via api/tokens.ts (secure-store native / localStorage web). i18n is Hermes-safe (no Intl.PluralRules). Use palette-aware components from components/ui.tsx. api/types.ts is a hand-written subset that drifts — reconcile via the api-contract skill. Gate: npm run typecheck. See mobile/CLAUDE.md and the mobile-dev skill."
else
  emit "Backend stack pillars (src/seedbank/): (1) async end-to-end (no sync DB in handlers), (2) layered routers → services → repositories → ORM (no skipping), (3) Pydantic at boundaries (Envelope/Page, never raw dict), (4) all config via core/config.Settings, (5) every detection traceable via inferences.model_id. See CLAUDE.md and the backend-dev skill."
fi

exit 0
