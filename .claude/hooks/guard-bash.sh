#!/usr/bin/env bash
# PreToolUse hook for Bash: deny destructive or unsafe commands.
# Returns JSON {"hookSpecificOutput":{"permissionDecision":"deny",...}} to abort.
# Otherwise prints nothing and exits 0 (allow).

set -euo pipefail

input="$(cat || true)"

cmd=""
if command -v jq >/dev/null 2>&1; then
  cmd="$(echo "$input" | jq -r '.tool_input.command // empty' 2>/dev/null || true)"
fi

[[ -z "${cmd}" ]] && exit 0

deny() {
  local reason="$1"
  cat <<JSON
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"${reason}"}}
JSON
  exit 0
}

# 1. git force-push to main/master is never OK.
if echo "${cmd}" | grep -Eq 'git[[:space:]]+push.*(--force|-f([[:space:]]|$)).*((origin|upstream)[[:space:]]+(main|master)|HEAD:(main|master))'; then
  deny "Force-pushing to main/master is blocked."
fi

# 2. Any push to main/master.
if echo "${cmd}" | grep -Eq 'git[[:space:]]+push.*(origin|upstream)[[:space:]]+(main|master)([[:space:]]|$)'; then
  deny "Push to main/master is blocked. Push a feature branch and open a PR."
fi

# 3. rm -rf on top-level paths.
if echo "${cmd}" | grep -Eq 'rm[[:space:]]+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r)([[:space:]]+--)?[[:space:]]+(/|/\*|\*|~|\$HOME|\.)([[:space:]]|$)'; then
  deny "Refusing rm -rf on a top-level path. Be specific."
fi

# 4. Soft warning for alembic upgrade head (allowed but reminded).
if echo "${cmd}" | grep -Eq '^[[:space:]]*alembic[[:space:]]+upgrade[[:space:]]+head'; then
  echo "Note: alembic upgrade head runs against \$DATABASE_URL. Confirm it's the dev DB." >&2
fi

exit 0
