#!/usr/bin/env bash
# End-to-end smoke test for a running seed-bank stack.
#
# Verifies the *running* compose stack — not unit/integration tests
# (which use testcontainers and don't catch issues like "torch missing
# from the worker-inference image" or "worker-cpu OOMs because concurrency
# is wrong").
#
# Exit status is the gate. Logs are noisy on purpose so a failing run
# tells the operator exactly which step broke.
#
# Usage:
#   make smoke
#   API_PORT=58080 SEED_END_USER_PASSWORD=... ./scripts/smoke.sh
#
# Required env (with defaults):
#   API_PORT                   default 58080
#   SEED_END_USER_EMAIL        default user@seedbank.dev
#   SEED_END_USER_PASSWORD     default UserDemo123! (matches seed_dev defaults)
#   SMOKE_IMAGE                default data/test-images/maize-test/image2.png
#   SMOKE_TIMEOUT_SEC          default 240 (analyze on CPU is ~75s; pad for cold start)

set -euo pipefail

API_PORT="${API_PORT:-58080}"
EMAIL="${SEED_END_USER_EMAIL:-user@seedbank.dev}"
PASSWORD="${SEED_END_USER_PASSWORD:-UserDemo123!}"
IMAGE="${SMOKE_IMAGE:-data/test-images/maize-test/image2.png}"
TIMEOUT_SEC="${SMOKE_TIMEOUT_SEC:-240}"
BASE="http://localhost:${API_PORT}"

log() { printf "[smoke] %s\n" "$*"; }
fail() { printf "[smoke] FAIL: %s\n" "$*" >&2; exit 1; }

require() {
    command -v "$1" >/dev/null 2>&1 || fail "missing required tool: $1"
}

require curl
require python3
[ -f "$IMAGE" ] || fail "test image not found: $IMAGE"

# 1. /readyz — give the stack 60s to come up cold.
log "waiting for ${BASE}/readyz ..."
for i in $(seq 1 30); do
    if curl -fsS "${BASE}/readyz" >/dev/null 2>&1; then
        log "api ready (after ${i} attempts)"
        break
    fi
    sleep 2
    if [ "$i" = "30" ]; then
        fail "api did not become ready within 60s"
    fi
done

# 2. Login.
log "login as ${EMAIL}"
LOGIN_RESP=$(curl -fsS -X POST "${BASE}/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}")
TOKEN=$(printf "%s" "$LOGIN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")
[ -n "$TOKEN" ] || fail "login returned empty access_token"

# 3. Submit analyze. We don't pin a seed_type — model selection falls back to
#    the global production detector (provisioned by ``make provision-smoke-model``).
log "submitting ${IMAGE} to /api/v1/analyze"
ANALYZE_RESP=$(curl -fsS -X POST "${BASE}/api/v1/analyze" \
    -H "authorization: Bearer ${TOKEN}" \
    -F "files=@${IMAGE}")
BATCH_ID=$(printf "%s" "$ANALYZE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])")
[ -n "$BATCH_ID" ] || fail "analyze did not return a batch id"
log "batch ${BATCH_ID} submitted"

# 4. Poll until terminal or timeout.
deadline=$(( $(date +%s) + TIMEOUT_SEC ))
status=""
while [ "$(date +%s)" -lt "$deadline" ]; do
    BATCH_RESP=$(curl -fsS "${BASE}/api/v1/batches/${BATCH_ID}" \
        -H "authorization: Bearer ${TOKEN}")
    status=$(printf "%s" "$BATCH_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['status'])")
    log "  status=${status}"
    case "$status" in
        succeeded|partial)
            duration=$(printf "%s" "$BATCH_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['data'].get('duration_ms'))")
            [ "$duration" != "None" ] || fail "terminal status but duration_ms is null"
            log "OK: status=${status} duration_ms=${duration}"
            exit 0
            ;;
        failed)
            fail "batch finished with status=failed; see worker logs"
            ;;
        pending|running)
            sleep 5
            ;;
        *)
            fail "unexpected status: ${status}"
            ;;
    esac
done

fail "batch did not reach a terminal state within ${TIMEOUT_SEC}s (last status=${status})"
