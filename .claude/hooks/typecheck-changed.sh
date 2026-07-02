#!/usr/bin/env bash
# PostToolUse hook: type-check the file just edited (only under src/seedbank/).
# Surfaces type errors to Claude as additional context — does NOT block.
# Tolerant: silently skips if mypy isn't installed.

set -euo pipefail

input="$(cat || true)"

file=""
if command -v jq >/dev/null 2>&1; then
  file="$(echo "$input" | jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null || true)"
fi

[[ -z "${file}" ]] && exit 0
[[ "${file}" != *.py ]] && exit 0
[[ "${file}" != */src/seedbank/* ]] && exit 0
[[ ! -f "${file}" ]] && exit 0

if ! command -v mypy >/dev/null 2>&1; then
  exit 0
fi

# Run mypy on this file. If clean, exit silently; if errors, print them so
# the harness echoes them back to Claude as a tool-result reminder.
output="$(mypy --hide-error-context --no-color-output --no-error-summary "${file}" 2>&1 || true)"

if [[ -n "${output}" ]]; then
  echo "mypy findings on $(basename "${file}"):"
  echo "${output}"
fi

exit 0
