---
description: The canonical "is my change green?" gate — ruff format check, ruff check, mypy strict, and the fast unit subset
allowed-tools: Bash, Read, Grep, Glob
---

# /check

Thin wrapper around `make check`. CI's `check.yml` runs the same four steps on
every PR and master push, so a green local run means the quality gate will pass
in CI (review and the full pyramid still apply).

## Steps

Prefer `make check` — it owns the source of truth for flags so this command
never drifts. Run it and report the result:

```bash
cd /mnt/shared_data/FCAI/GP/project/seed-bank/
make check
```

`make check` expands to `lint typecheck test-unit`, i.e.:

```bash
ruff format --check .                                          # formatting
ruff check .                                                   # lint
mypy                                                           # strict, config-driven (no args)
pytest -m "unit or not integration and not e2e" tests/unit --cov-fail-under=0
```

If you need a per-step pass/fail breakdown (e.g. to point at the exact failing
step), run them individually instead of `make check`, but keep the flags
identical — diverging from the Makefile defeats the "mirror of CI" guarantee.

## Output format

```
ruff format --check  : pass
ruff check           : 3 errors
  - src/seedbank/api/v1/widgets.py:42 E501 line too long
  - ...
mypy                 : pass
pytest unit          : 87 passed in 4.2s

Overall: FAIL — fix the ruff check errors above and re-run /check.
```

When everything passes, end with:
`Overall: green. Run \`make test\` for the full pyramid (integration + e2e) before opening a PR.`

## Gotchas

- mypy takes no path argument — strictness and packages come from `pyproject.toml`.
  Passing `mypy src` would type-check a different set than CI and can mask or
  invent errors. Let the config drive it.
- The unit step uses `--cov-fail-under=0` on purpose: the coverage gate is
  temporarily relaxed (the project-wide `fail_under=80` is enforced by the full
  `make test`, to be ratcheted back as worker/ML/storage/OAuth holes fill; see
  [CI gates](../memory/workflow.md#ci-gates)). Don't add a coverage threshold here — it's a *fast* gate.

## Don't do

- Don't run `tests/integration` or `tests/e2e` here. They need testcontainers and
  are slow — that's `make test`.
- Don't auto-fix. The point is to surface problems for the developer to decide on.
  (`ruff format .` and `ruff check --fix .` are separate, deliberate actions.)
