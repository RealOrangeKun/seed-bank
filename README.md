# Seed-Bank

Production-grade seed quality analysis API.

> Repo is mid-revamp from the original prototype (now archived under
> `legacy/`) to an async FastAPI service with a real DB design, an ML
> registry, MinIO object storage, Celery + Redis, ClickHouse OLAP, and
> MLflow. See `CLAUDE.md` for stack pillars and `docs/operations.md`
> for the dev loop.

## Quick start

```bash
make env             # generate .env from .env.example
make up-infra        # postgres + redis + minio + clickhouse only — fast smoke
make up              # full stack (builds api image first time)
make migrate         # apply Alembic migrations
make test            # full test pyramid (unit + integration + e2e)
make check           # lint + typecheck + fast unit subset
make help            # everything else
```

`/api/v1/docs` is the OpenAPI UI once `make up` finishes.

## Layout

```
src/seedbank/        # application code (api → services → infrastructure → ORM)
alembic/versions/    # schema migrations (one per change, never edit applied)
models/              # trained .pth files — uploaded to MinIO at bootstrap
tests/               # unit / integration / e2e / load + factories
scripts/             # seed_dev, register_model, run_experiment
docs/                # architecture, auth, ml-platform, dwh, operations
legacy/              # archived prototype, do not import from here
```

## Stack pillars (from `CLAUDE.md`)

1. Async end-to-end (FastAPI + SQLAlchemy 2.0 async + asyncpg).
2. Layered architecture: routers → services → repositories → ORM. No
   skipping, no leaks.
3. Pydantic v2 at request/response boundaries; framework-free domain.
4. All config via one `Settings(BaseSettings)` in `core/config.py`.
5. Every detection traces back to `inferences.model_id`.

## Status

Phases 1–9 landed: scaffold, schema, repos + clients, auth (bcrypt +
JWT + OAuth + API keys + RBAC), ML platform (registry, backends, model
manager, traffic-split router, `/api/v1/models`), the unified inference
path (`POST /analyze` + Celery batch), experiments + MLflow, the DWH
(OLTP → ClickHouse, implemented as Celery dual-write rather than logical
replication), and observability (`/metrics` + OTel + Sentry, opt-in).

Outstanding — the original **Phase 10** (load tests, full e2e coverage,
docs polish) plus CI/CD, which was never scoped. See
[`docs/revamp-status.md`](docs/revamp-status.md) for the full reconstructed
state, the remaining-work list, and the resume roadmap.

## License

Proprietary.
