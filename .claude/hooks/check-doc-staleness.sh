#!/usr/bin/env bash
# PostToolUse hook: after an edit to a schema-shaped or architecture-shaped file
# (models.py, an alembic migration, or an api/v1 router), print a NON-BLOCKING
# reminder to run the docs-sync skill and update the affected diagram. The docs
# go stale silently otherwise — this nudges the author while the change is fresh.
#
# House style (see inject-stack-reminder.sh): never block, always exit 0, and
# degrade gracefully if jq/grep are missing. An advisory hook that errors is
# worse than no hook — it interrupts the edit it was meant to annotate.

set -uo pipefail

input="$(cat || true)"

# Pull the edited file path out of the tool input. No jq -> no path -> stay quiet.
path=""
if command -v jq >/dev/null 2>&1; then
  path="$(echo "$input" | jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null || true)"
fi

# Nothing to inspect — exit clean, no noise.
if [ -z "$path" ]; then
  exit 0
fi

# Match the file against the doc-relevant surfaces. grep missing -> stay quiet.
reminder=""
if command -v grep >/dev/null 2>&1; then
  if echo "$path" | grep -Eq 'infrastructure/db/models\.py$'; then
    reminder="You edited the ORM models (models.py). A table/column/FK change usually means docs/diagrams/05-db-erd.md is now stale."
  elif echo "$path" | grep -Eq 'alembic/versions/.*\.py$'; then
    reminder="You added/edited an Alembic migration. If it changes the schema, docs/diagrams/05-db-erd.md likely needs the same change."
  elif echo "$path" | grep -Eq 'api/v1/[^/]+\.py$'; then
    reminder="You edited an api/v1 router. A new/changed endpoint surface usually means docs/diagrams/03-api-components.md is now stale."
  fi
fi

# No match -> not a doc-relevant edit -> stay quiet.
if [ -z "$reminder" ]; then
  exit 0
fi

cat <<JSON
{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"Docs may be stale: ${reminder} Run the docs-sync skill to update the affected diagram(s) and the prose in docs/system-overview.md + docs/revamp-status.md. Touch only what changed — no blanket redraw. This is advisory, not blocking."}}
JSON

exit 0
