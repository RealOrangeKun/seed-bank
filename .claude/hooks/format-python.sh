#!/usr/bin/env bash
# PostToolUse hook: format and lint-fix any Python file just edited under src/ or tests/.
# Tolerant: silently skips if ruff isn't installed (early-revamp state).

set -euo pipefail

# Read the tool-invocation JSON from stdin.
input="$(cat || true)"

# Extract the file_path field. Try multiple shapes (Edit, Write, MultiEdit).
file=""
if command -v jq >/dev/null 2>&1; then
  file="$(echo "$input" | jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null || true)"
fi

# Bail if we can't determine the file or it's not under our managed dirs or not Python.
[[ -z "${file}" ]] && exit 0
[[ "${file}" != *.py ]] && exit 0
case "${file}" in
  */src/seedbank/*|*/tests/*|*/scripts/*) ;;
  *) exit 0 ;;
esac
[[ ! -f "${file}" ]] && exit 0

# Run ruff if available; otherwise no-op.
if command -v ruff >/dev/null 2>&1; then
  ruff format "${file}" >/dev/null 2>&1 || true
  ruff check --fix --quiet "${file}" >/dev/null 2>&1 || true
fi

exit 0
