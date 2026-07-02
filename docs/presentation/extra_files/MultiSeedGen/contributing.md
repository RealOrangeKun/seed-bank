# Contributing

This is a small, single-maintainer project, but it holds a strict reproducibility
contract (see [architecture.md](architecture.md)). The tooling below exists to keep that
contract enforced automatically.

## Dev setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # add web/rembg/sam if you touch those paths
pre-commit install               # runs ruff + ruff-format (+ frontend prettier/eslint) per commit
```

## The regression gate

Run this before every commit — it is exactly what CI runs:

```bash
ruff check .                     # lint
ruff format --check .            # formatting
mypy multiseedgen                # type check
pytest -m "not gpu and not golden"   # tests (GPU + host-pinned golden tests skipped — exactly what CI runs)
```

All four must be green. The portable marker skips the host-pinned `golden` tests (same as
CI); run them locally too — `pytest tests/test_golden.py` — since they and
`tests/test_determinism.py` guard the byte-identity contract. A diff there means your change
altered generated pixels.

## Frontend (web UI)

The web UI source lives in [`frontend/`](../frontend) (React + TypeScript + Vite +
Tailwind v4 + Radix UI). It builds into `multiseedgen/web/static/`, and **that built output
is committed** so `pip install` / Docker need no Node toolchain. Node 22 LTS (see
`frontend/.nvmrc`).

Dev loop — run the backend and the Vite dev server side by side (Vite proxies `/api` +
`/ws` to `:8000`, so there's no CORS to configure):

```bash
multiseedgen-web                 # backend on :8000 (terminal 1)
cd frontend && npm ci && npm run dev   # UI on :5173, hot-reload (terminal 2)
```

Frontend gate (what CI's `frontend` job runs — all must be green; Prettier `format:check` runs
in pre-commit, not this job):

```bash
cd frontend
npm run lint           # ESLint (typescript-eslint, react-hooks, jsx-a11y)
npm run typecheck      # tsc --noEmit (strict)
npm run test           # Vitest + Testing Library
npm run build          # tsc + vite build -> ../multiseedgen/web/static (commit the result)
```

After any UI change, **run `npm run build` and commit the regenerated
`multiseedgen/web/static/` assets** alongside your source change — CI rebuilds and a stale
bundle will surface as a tracked-file diff. (`frontend/.npmrc` sets `legacy-peer-deps` so
`npm ci` resolves the one plugin whose peer range trails ESLint 10.)

## Tests

| Location | Scope | Speed |
|----------|-------|-------|
| `tests/unit/` | isolated single-function units | sub-second |
| `tests/` | integration & contract (determinism, golden, config/schema/cache snapshots, web) | seconds |
| `frontend/src/**/*.test.{ts,tsx}` | UI units & components (Vitest + Testing Library) | seconds |

Conventions for new tests:

- **Arrange–Act–Assert**, one behaviour per test, descriptive `test_<unit>_<behaviour>` names.
- Keep units **isolated and deterministic** — no network, no GPU, fixed PRNG seeds. Use
  the fixtures in `tests/unit/conftest.py` (`make_cfg`, `seed_cutout`, `seed_on_uniform_bg`, `rng`).
- Use `pytest.mark.parametrize` for matrices (methods, kinds, invalid inputs).
- Mark slow/end-to-end tests `@pytest.mark.slow`, GPU tests `@pytest.mark.gpu`,
  host-pinned byte tests `@pytest.mark.golden`.

Markers are strict (`--strict-markers`); a typo'd marker fails collection.

### Regenerating golden manifests

The golden byte manifests are pinned to this host's `numpy`/`opencv` versions. After a
**reviewed, intentional** change to those deps (or a deliberate pixel-affecting change),
regenerate and commit the new manifests:

```bash
UPDATE_GOLDEN=1 pytest tests/test_golden.py
```

Never regenerate to "make the test pass" — a golden diff you didn't expect is a real
regression in the determinism contract.

## Coding conventions

- **Config is the single source of truth.** New options go in `config.py` (with a
  `Literal` for choices and a range check that *raises* if needed), then wired into the
  CLI table and the web schema. Validators must never mutate gated values (see the
  determinism rules in [architecture.md](architecture.md)).
- **No `sys.exit()` / `print()` in library code.** Raise a `MultiSeedGenError` subclass;
  log via `logging.getLogger(__name__)`.
- **Preserve RNG draw order** in any compositing/degradation change, and keep the
  segmentation cache key (`SEG_VERSION`, `_seg_params_signature`) stable unless you
  intend to invalidate caches.
- Line length 100; `ruff format` is authoritative. Public re-exports are the only
  sanctioned unused imports (already allow-listed in `pyproject.toml`).
