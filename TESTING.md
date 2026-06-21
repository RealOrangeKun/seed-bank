# Testing

The project has an automated [`pytest`](pytest.ini) suite plus a few legacy manual scripts.

## Automated suite

Layout under `tests/`:
- `tests/unit/` — pure-function tests (confidence math, device fingerprinting). No DB, no weights.
- `tests/api/` — endpoint tests via FastAPI `TestClient` with a **mocked** `ModelManager`
  (no model weights needed). Persisting endpoints are marked `integration`.
- `tests/integration/` — DB-backed `app.crud` tests (ownership isolation, stats math).
- `tests/conftest.py` — fixtures: `client` (mocked models), `db_session`, `png_bytes`.

### Run it
```bash
# 1) A PostgreSQL for the DB-backed tests (host port 5433 here; 5432 is often taken).
docker run -d --name seed_bank_postgres \
  -e POSTGRES_USER=seedbank -e POSTGRES_PASSWORD=seedbank_dev_password -e POSTGRES_DB=seedbank_db \
  -p 5433:5432 postgres:17-alpine
export DATABASE_URL="postgresql+psycopg://seedbank:seedbank_dev_password@localhost:5433/seedbank_db"
.venv/bin/alembic upgrade head

# 2) Dev deps (note: httpx<0.28 for the fastapi 0.109 TestClient).
.venv/bin/pip install -r requirements-dev.txt

# 3) Run.
.venv/bin/python -m pytest                    # everything
.venv/bin/python -m pytest -m "not integration"  # skip DB-backed tests
```
The test database URL can be overridden with `TEST_DATABASE_URL`.

### Why models are mocked
The real `.pth` weights are large and not in git, so `tests/conftest.py` installs a
`FakeModelManager` and patches `detect_seeds`/`classify_seeds`. This exercises every endpoint's
request validation, persistence, and response shaping without GPU/weights. The pure ML math is
unit-tested directly against `calculate_confidence_from_logits`.

## Legacy manual scripts
`tests/test_api.py`, `tests/test_batch_api.py`, and `tests/test_confidence_metrics.py` are
**manual** scripts that hit a running server on `:8000` (and need real weights). They are
excluded from `pytest` collection. Run them by hand against a live server if desired:
```bash
.venv/bin/python tests/test_api.py
```

## Linting
```bash
.venv/bin/ruff check .
```

## CI
GitHub Actions runs ruff + the suite (with a Postgres service) on every push/PR —
see `.github/workflows/ci.yml`.
