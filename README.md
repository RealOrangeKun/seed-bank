# Seed-Bank

**v1.0.0** — Seed quality analysis platform: point a camera (web or mobile) at
a batch of seeds and get a good/bad breakdown back, powered by a real ML
pipeline (detection + quality classification, model registry, experiments).

> The legacy prototype is archived under `legacy/`. The platform is now an
> async FastAPI service with a real DB design, an ML registry, MinIO object
> storage, Celery + Redis, ClickHouse OLAP, a bilingual (EN/AR + RTL)
> React web app, and a React Native (Expo) mobile app.

## What's here

| | |
|---|---|
| **Backend** (`src/seedbank/`) | Async FastAPI API — auth, ML platform, inference, DWH, observability |
| **Frontend** (`frontend/`) | React + Vite SPA — farmer + admin/ML-platform surfaces, full EN/AR i18n |
| **Mobile** (`mobile/`) | Expo / React Native app — realtime camera capture → analyze → results |

See [`frontend/README.md`](frontend/README.md) and [`mobile/README.md`](mobile/README.md)
for the details of each client.

## Quick start

```bash
make env             # generate .env from .env.example
make up               # full stack: api + workers + postgres + redis + minio + clickhouse
make migrate          # apply Alembic migrations
make seed             # demo users + sample data (see Demo credentials below)
make up-front         # optional: frontend on :5173 via the Docker nginx image
```

- API: `http://localhost:8000` (`/api/v1/docs` for the OpenAPI UI)
- Frontend: `http://localhost:5173` (or `cd frontend && npm install && npm run dev`)
- Mobile: `cd mobile && npm install && npm start` (press `w` for the browser, or scan the QR with Expo Go)

```bash
make test             # full test pyramid (unit + integration + e2e)
make check            # lint + typecheck + fast unit subset
make help             # everything else
```

### Demo credentials

Seeded by `make seed` (`scripts/seed_dev.py`), one account per role:

| Role | Email | Password |
|---|---|---|
| Admin | `admin@seedbank.dev` | `AdminDemo123!` |
| AI developer | `ai-dev@seedbank.dev` | `AiDevDemo123!` |
| End user | `user@seedbank.dev` | `UserDemo123!` |

## Layout

```
src/seedbank/        # application code (api → services → infrastructure → ORM)
alembic/versions/    # schema migrations (one per change, never edit applied)
models/              # trained .pth files — uploaded to MinIO at bootstrap
tests/               # unit / integration / e2e / load + factories
scripts/             # seed_dev, register_model, run_experiment
docs/                # architecture, auth, ml-platform, dwh, operations, system overview
frontend/            # React + Vite web app (EN/AR + RTL)
mobile/              # Expo / React Native app
legacy/              # archived prototype, do not import from here
```

## Stack pillars

1. Async end-to-end (FastAPI + SQLAlchemy 2.0 async + asyncpg).
2. Layered architecture: routers → services → repositories → ORM. No
   skipping, no leaks.
3. Pydantic v2 at request/response boundaries; framework-free domain.
4. All config via one `Settings(BaseSettings)` in `core/config.py`.
5. Every detection traces back to `inferences.model_id`.

## Status

**v1.0.0 (beta)** — backend (auth, ML platform, unified inference path,
experiments, the OLTP→ClickHouse DWH, observability) plus a fully
localized web app and a new mobile app are all in place and manually verified
end-to-end. See [`docs/system-overview.md`](docs/system-overview.md) for the
full architecture and [`docs/revamp-status.md`](docs/revamp-status.md) for the
backend's phase-by-phase history.

Outstanding: load tests, full e2e coverage, CI/CD — not yet scoped.

## License

Proprietary.
