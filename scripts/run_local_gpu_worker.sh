#!/usr/bin/env bash
# Run the inference Celery worker locally in the .venv so it uses the host's
# NVIDIA GPU (the dockerized worker-inference is a CPU torch build with no GPU
# passthrough). Points at the dev stack's host-published ports. Stop the
# dockerized worker first so they don't both drain the `inference` queue:
#
#   docker compose stop worker-inference
#   scripts/run_local_gpu_worker.sh
#
set -euo pipefail
cd "$(dirname "$0")/.."

# Load dev secrets/values from .env, then override the in-network hostnames
# with the host-published ports (see compose.override.yaml).
set -a; source .env; set +a

export POSTGRES_DSN="postgresql+asyncpg://${POSTGRES_USER:-seedbank}:${POSTGRES_PASSWORD:-seedbank}@localhost:5442/${POSTGRES_DB:-seedbank}"
export REDIS_DSN="redis://localhost:6379/0"
export CELERY_BROKER_URL="redis://localhost:6379/1"
export CELERY_RESULT_BACKEND="redis://localhost:6379/2"
export MINIO_ENDPOINT="localhost:9000"
export MINIO_PUBLIC_ENDPOINT="localhost:9000"
export CLICKHOUSE_HOST="localhost"

exec .venv/bin/celery -A seedbank.workers.celery_app worker \
  --loglevel=info -Q inference,evaluation \
  --concurrency="${WORKER_INFERENCE_CONCURRENCY:-1}" \
  --max-tasks-per-child="${WORKER_INFERENCE_MAX_TASKS_PER_CHILD:-50}"
