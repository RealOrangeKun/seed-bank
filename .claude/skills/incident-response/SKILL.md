---
name: incident-response
description: On-call runbook for the seed-bank stack. Use when something is broken — failing healthchecks, alert from Prometheus, error spike in logs, latency regression, or a user reports the API isn't working.
---

# Incident response runbook

## Purpose

Get from "something is broken" to a diagnosis and a safe recovery action,
without destroying the evidence the post-mortem will need. Most outages on this
stack are recoverable; the harm usually comes from reacting before
understanding.

## When to use

Failing healthchecks, a Prometheus alert, an error spike in logs, a latency
regression, or a user reporting the API is down.

## First rule

**Don't restart anything for the first five minutes — gather state.** A restart
clears the in-memory and log evidence that explains the root cause, and the
incident recurs because you fixed the symptom, not the cause.

## Steps

### 0. Triage in order

1. Is the API answering at all? `curl -fsSL http://localhost:8000/healthz`
2. Is it ready? `curl -fsSL http://localhost:8000/readyz` (probes DB, Redis,
   MinIO, ClickHouse, and that a production model is loaded).
3. What does Prometheus show? Open `/metrics` or your dashboard.
4. What's in the logs?
   `docker compose logs --tail=200 api worker-cpu worker-inference`

### 1. Healthchecks

| Probe | Returns 503 when | First look |
|---|---|---|
| `/healthz` | Process is dead — Compose restarts it; find out why it died | `docker compose ps`, `docker compose logs api` |
| `/readyz` | A dependency is unreachable or no production model is loaded | the dep checks below |

```bash
# Postgres
docker compose exec postgres pg_isready -U seedbank
# Redis
docker compose exec redis redis-cli ping
# MinIO
curl -fsSL http://localhost:9000/minio/health/ready
# ClickHouse
curl -fsSL http://localhost:8123/ping
# Model loaded?
docker compose logs worker-inference | grep model_manager.loaded
```

### 2. Common failure modes

#### "readyz fails / analyze returns model-not-ready"

The analyze pipeline needs a **production detection model** loaded to route a
scan to. If none is promoted — common on a fresh local or CI environment —
`/readyz` flags it and analyze raises `ModelNotReadyError`.

- Check what's promoted:
  ```sql
  SELECT kind, seed_type_id, name, version, status
  FROM model_artifacts WHERE status = 'production';
  ```
- For a real deployment, re-promote a known-good model via the registry (see
  the rollback step below).
- For **local or CI** where no real weights exist, provision the tiny fixture
  detector — `make provision-smoke-model` — so the pipeline has something to
  resolve. See [analyze needs a model](../../memory/known-issues.md#analyze-needs-a-promoted-detection-model) for what it does and its caveats
  (idempotent, CI/dev only, never a real deployment).

#### "auth never works after a restart"

Likely a JWT key mismatch (the secret was lost or rotated). Verify
`SEEDBANK_JWT_SECRET` matches what signed the existing tokens. Rotating the
secret invalidates every token issued before it — that is by design; tell users
to re-login.

#### "analyze hangs / 504"

- Worker stuck:
  `docker compose exec worker-inference celery -A seedbank.workers.celery_app inspect active`.
- GPU contention: `nvidia-smi` on the host.
- A specific image is malformed: check the Celery task's exception in the
  result backend.

#### "stats show 0 / look stale"

The DWH dual-write task is failing. Stats come from ClickHouse, written by a
Celery task on `worker-cpu` (the `dwh` queue) — **not** logical-replication CDC;
see [DWH dual-write](../../memory/decisions.md#dwh-is-app-level-dual-write-not-cdc). If the task errors, the dashboard freezes at the
last good value.

```bash
docker compose logs worker-cpu | grep -E 'dwh|clickhouse'
# Is dwh_enabled on, and is ClickHouse reachable from the worker?
curl -fsSL http://localhost:8123/ping
```

Watch the `seedbank_dwh_dispatch_total{result="error"}` metric. If dispatch is
`disabled`, `DWH_ENABLED` is off; if `error`, ClickHouse is unreachable or the
insert is failing — check the worker logs and restart `worker-cpu` if wedged.

#### "a model produces garbage after deploy"

- Did the builder file change? It shouldn't have:
  `git log --oneline src/seedbank/infrastructure/ml/builders/`.
- Did the weights URI change?
  `SELECT name, version, artifact_uri, status FROM model_artifacts WHERE seed_type_id = ...;`.
- Roll back via the registry (atomic, reversible):
  ```bash
  python scripts/register_model.py promote --model-id <previous> --to production
  ```

#### "401s spike"

- JWT secret rotated — see above.
- Clock skew — check NTP on the API host.
- Refresh-token reuse detection fired and revoked a family. Look for
  `auth.refresh_reuse_detected` in logs; under attack this is correct behavior.
  Check the source IP.

#### "rate limit triggering on every user"

The rate limiter's Redis was likely wiped or its key namespace is misconfigured,
so requests share a bucket. Inspect `api/rate_limit.py` and the Redis keys.

#### "MinIO presigned upload fails with 403"

- Clock skew between the API host and MinIO.
- A bucket policy changed.
- The signed URL expired (5–15 min default); the client should re-request a
  presign and retry.

### 3. Useful queries

```sql
-- Postgres: most recent failed batches
SELECT id, user_id, status, error_message, finished_at
FROM scan_batches
WHERE status = 'failed'
ORDER BY finished_at DESC
LIMIT 50;
```

```sql
-- ClickHouse: latency regression, last hour vs the prior hour
SELECT
  toStartOfHour(occurred_at)      AS hour,
  model_id,
  count()                         AS n,
  quantileExact(0.5)(latency_ms)  AS p50,
  quantileExact(0.95)(latency_ms) AS p95
FROM fact_inference
WHERE occurred_at >= now() - INTERVAL 2 HOUR
GROUP BY hour, model_id
ORDER BY hour DESC, p95 DESC;
```

## Conventions

- Gather before you act; restart only once you understand what died.
- Prefer registry/traffic operations over container restarts — they're atomic
  and reversible, so a wrong call is easy to undo.

### Safe recovery actions (no approval needed)

- Restart a worker: `docker compose restart worker-cpu` / `worker-inference`.
- Restart the API: `docker compose restart api`.
- Re-promote a previous model via `register_model.py promote` — atomic and
  reversible.
- Provision the smoke detector in local/CI when the symptom is "no model
  loaded" (never in a real deployment).
- Drain a wedged Celery queue:
  `celery -A seedbank.workers.celery_app purge` — only if it's full of poison
  messages and you've logged them elsewhere first.

### Actions that require approval

- Restarting Postgres (drops connections; users see 5xx briefly).
- Truncating any table.
- Running an Alembic migration in prod (follow the staged-deploy plan in the
  `db-migration` skill).
- Rotating the JWT secret (invalidates all sessions).
- Changing a `traffic_splits` row outside a maintenance window.

## Gotchas

- `/readyz` failing for "no production model" looks like an outage but on a
  fresh environment it just means nothing was promoted yet — provision or
  promote before assuming the worst.
- A restart that "fixes it" without a known cause is a deferred incident, not a
  resolved one. Capture the logs first.

## Post-incident

Even short incidents get a one-pager: timeline (UTC); what broke (one
sentence); why (root cause, not symptom); how we recovered; what stops it
recurring (an alert? a test? a tighter constraint?). Save it under
`docs/postmortems/<YYYY-MM-DD>-<slug>.md` — the next on-call person will thank
you.

## Checklist

- [ ] Gathered `/healthz`, `/readyz`, metrics, and logs before touching anything
- [ ] Identified the failing dependency or subsystem, not just the symptom
- [ ] Chose the narrowest safe recovery action
- [ ] Got approval for any high-blast-radius action
- [ ] Wrote the post-mortem one-pager
