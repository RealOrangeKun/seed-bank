# Seed-Bank dev workflow.
# Usage: `make help` for the full list.

SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

PYTHON ?= python3.12
VENV   ?= .venv
PIP    := $(VENV)/bin/pip
PY     := $(VENV)/bin/python
COMPOSE ?= docker compose

# Host port the api publishes on. compose.override.yaml may shift this;
# `make up` reads it via this variable so wait/curl hit the right address.
API_PORT ?= 58080

.PHONY: help
help: ## Show this help.
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort

# ── Local Python env ────────────────────────────────────────────────────────
.PHONY: venv install install-inference
venv: ## Create a local virtualenv.
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip uv

install: venv ## Install runtime + dev deps locally.
	$(VENV)/bin/uv pip install -e ".[dev]"

install-inference: venv ## Install ML deps locally (heavy).
	$(VENV)/bin/uv pip install -e ".[dev,inference]"

# ── Compose lifecycle ───────────────────────────────────────────────────────
.PHONY: env up up-infra up-gpu up-dev up-obs up-prod down down-prod restart logs logs-prod ps wait secrets-check
env: ## Create .env from .env.example if missing. Idempotent.
	@if [ ! -f .env ]; then cp .env.example .env && echo "created .env from .env.example"; \
	 else echo ".env already present"; fi

up-infra: env ## Start ONLY infra (postgres, redis, minio, clickhouse). No build, fast smoke.
	$(COMPOSE) up -d postgres redis minio clickhouse
	@echo "infra up. host ports follow compose.override.yaml if present."
	@$(COMPOSE) ps --format "table {{.Service}}\t{{.Health}}\t{{.Ports}}"

up: env ## Start the full lean stack (api + infra). Builds the api image first time (slow once, fast after).
	$(COMPOSE) up -d --build api postgres redis minio clickhouse mlflow
	@$(MAKE) wait

up-gpu: env ## Start including the GPU inference worker.
	$(COMPOSE) --profile gpu up -d --build
	@$(MAKE) wait

up-dev: env ## Start with adminer for quick DB poking.
	$(COMPOSE) --profile dev up -d --build api postgres redis minio clickhouse mlflow adminer
	@$(MAKE) wait

up-obs: env ## Start the lean stack PLUS prometheus + grafana (obs profile).
	$(COMPOSE) --profile obs up -d --build api postgres redis minio clickhouse mlflow prometheus grafana
	@$(MAKE) wait

# In prod the grafana password comes from `./secrets/grafana_admin_password`
# via `GF_SECURITY_ADMIN_PASSWORD__FILE`. The dev compose still
# interpolates `GRAFANA_PASSWORD` for `GF_SECURITY_ADMIN_PASSWORD` at
# config-load time, so we set a dummy here to satisfy the `:?` guard
# without using the value (the prod overlay's `GF_SECURITY_ADMIN_PASSWORD__FILE`
# wins inside the container).
PROD_COMPOSE_ENV := GRAFANA_PASSWORD=unused-see-secrets-grafana_admin_password
PROD_COMPOSE := $(PROD_COMPOSE_ENV) $(COMPOSE) -f compose.yaml -f compose.prod.yaml

up-prod: secrets-check ## Start the full prod overlay (secrets-checked, GPU on, ports locked down). No build — uses pre-built images.
	$(PROD_COMPOSE) up -d
	@echo "prod stack up. api on :8000, grafana on :3000. everything else internal."
	@$(PROD_COMPOSE) ps

down-prod: ## Stop the prod overlay (keeps volumes).
	$(PROD_COMPOSE) down

logs-prod: ## Follow prod-overlay logs.
	$(PROD_COMPOSE) logs -f --tail=200

secrets-check: ## Verify ./secrets/* are present and chmod 0400. Fails CI-style if not.
	@set -e; \
	required="postgres_password jwt_secret minio_access_key minio_secret_key clickhouse_password roboflow_api_key sentry_dsn grafana_admin_password"; \
	missing=0; bad=0; \
	for f in $$required; do \
	  path="secrets/$$f"; \
	  if [ ! -f "$$path" ]; then \
	    echo "MISSING: $$path"; missing=$$((missing+1)); continue; \
	  fi; \
	  mode=$$(stat -c %a "$$path"); \
	  if [ "$$mode" != "400" ]; then \
	    echo "BAD MODE: $$path is $$mode (want 400)"; bad=$$((bad+1)); \
	  fi; \
	done; \
	if [ $$missing -ne 0 ] || [ $$bad -ne 0 ]; then \
	  echo "secrets-check FAILED ($$missing missing, $$bad wrong perms)"; \
	  echo "see secrets/README.md for setup."; \
	  exit 1; \
	fi; \
	echo "secrets-check OK ($$(echo $$required | wc -w) files, 0400)"

down: ## Stop and remove containers (keeps volumes).
	$(COMPOSE) down

down-volumes: ## Stop everything AND wipe volumes — total reset.
	$(COMPOSE) down -v

restart: down up ## Restart everything cleanly.

logs: ## Follow logs for all services.
	$(COMPOSE) logs -f --tail=200

ps: ## Show service status.
	$(COMPOSE) ps

wait: ## Wait until api becomes healthy.
	@echo "waiting for api /readyz on http://localhost:$(API_PORT) ..."
	@for i in $$(seq 1 60); do \
	  if curl -fsS http://localhost:$(API_PORT)/readyz >/dev/null 2>&1; then \
	    echo "api ready"; exit 0; \
	  fi; sleep 2; \
	done; echo "api did not become ready"; $(COMPOSE) ps; exit 1

# ── Migrations / seed ────────────────────────────────────────────────────────
.PHONY: migrate migrate-down migrate-clickhouse seed
migrate: ## Apply Alembic migrations against the dev DB.
	$(COMPOSE) exec api alembic upgrade head

migrate-down: ## Roll back one Alembic revision.
	$(COMPOSE) exec api alembic downgrade -1

migrate-clickhouse: ## Apply ClickHouse star-schema DDL (idempotent).
	$(COMPOSE) exec api python -m scripts.init_clickhouse

seed: migrate-clickhouse ## Seed catalog, register models, create demo users.
	$(COMPOSE) exec api python -m scripts.seed_dev

# ── Quality gates ────────────────────────────────────────────────────────────
.PHONY: fmt lint typecheck check test test-unit test-integration test-e2e cov
fmt: ## Auto-format with ruff.
	$(VENV)/bin/ruff format .
	$(VENV)/bin/ruff check --fix .

lint: ## Lint without auto-fix.
	$(VENV)/bin/ruff format --check .
	$(VENV)/bin/ruff check .

typecheck: ## Strict mypy.
	$(VENV)/bin/mypy

check: lint typecheck test-unit ## Fast pre-commit gate.

test: ## Full test pyramid (unit + integration + e2e).
	$(VENV)/bin/pytest

test-unit: ## Unit tests only.
	$(VENV)/bin/pytest -m "unit or not integration and not e2e" tests/unit

test-integration: ## Integration tests (testcontainers).
	$(VENV)/bin/pytest -m integration tests/integration

test-e2e: ## Full e2e suite.
	$(VENV)/bin/pytest -m e2e tests/e2e

cov: ## Open coverage report (xml in CI, html locally).
	$(VENV)/bin/pytest --cov-report=html
	@echo "htmlcov/index.html"

# ── Image hygiene ────────────────────────────────────────────────────────────
.PHONY: image-bloat
image-bloat: ## Print top 30 largest files in the api image.
	docker run --rm seedbank/api:0.1.0 sh -c "du -ah /opt/venv /app 2>/dev/null | sort -rh | head -30"

# ── Cleanup ──────────────────────────────────────────────────────────────────
.PHONY: clean
clean: ## Remove caches, coverage, build artifacts.
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov coverage.xml dist build *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
