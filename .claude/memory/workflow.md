# Workflow

How a change moves from idea to merged, and what CI enforces. Indexed from
[`MEMORY.md`](MEMORY.md); the `/new-issue` and `/open-pr` commands drive this loop.

_Last updated: 2026-06-26_

## The change loop

Every change follows: **open an issue → branch → commit → PR that closes the
issue → merge.**

- **Issue** — use the templates (`bug.md` carries *Root cause* / *Fix*;
  `task.md` for non-bugs). The `/new-issue` command scaffolds one.
- **Branch** — `<type>/<slug>` (`fix/supplier-refresh`, `feat/big-features`).
  Never work on `master` directly.
- **Commit** — Conventional Commits with scope (`feat(frontend):`,
  `fix(models):`, `test(dwh):`, `ci:`, `chore:`), imperative lower-case subject,
  and **no trailer** — see [No Co-Authored-By
  trailer](conventions.md#no-co-authored-by-trailer).
- **PR** — body is `## What` (bullets, each ending `(Closes #N)` where relevant),
  optional `## Not included`, `## Test` (what you ran). The `/open-pr` command
  builds this and [stages explicitly](conventions.md#stage-explicit-paths).

Prefer the `/new-issue` and `/open-pr` commands so the format stays consistent.
CI gates the PR — see [CI gates](#ci-gates).

## CI gates

GitHub Actions under `.github/workflows/`:

- **On every PR and master** — `check.yml` (mirrors `make check`: `uv sync
  --frozen`, `uv lock --check`, ruff format + check, mypy strict) and `test.yml`
  (the full pytest pyramid).
- **On master** — `build.yml` (multi-stage image build; asserts **torch is not
  in the api image** — see [Lean
  Compose](decisions.md#lean-compose-without-degrading-quality)) and `smoke.yml`
  (compose e2e: env → up → migrate → seed → provision-smoke-model → smoke — see
  [analyze needs a
  model](known-issues.md#analyze-needs-a-promoted-detection-model)).

Two things to know:

- CI installs with **`uv sync --frozen`** (lockfile-pinned). A non-frozen install
  pulls newer libs and drifts mypy/deprecations red — keep `uv.lock` in step.
- The **coverage gate is temporarily relaxed** (`--cov-fail-under=0`) and meant
  to ratchet back up; coverage is measured but not yet enforced.

Run `/check` before opening a PR — green locally ≈ green in CI. Keep the `#51`
dwh xfail in place (see [the 4 DWH
tests](known-issues.md#the-4-dwh-tests-xfail-51)).
