---
description: Branch (if needed), commit the code changes, push, and open a PR in the house style — Conventional Commit + What/Test body, Closes #N
allowed-tools: Bash, Read, Glob, Grep
---

# /open-pr

Take the current working changes and turn them into a pull request that matches
how we ship: a `<type>/<slug>` branch, one Conventional-Commit, and a PR body
using the repo template. The goal is that a reviewer can read the PR without
reading the diff first.

Optional argument: an issue number to close (e.g. `/open-pr 50`). If none is
given, infer one from the branch name or recent commits, but never invent a
number — when in doubt, omit the `Closes` line.

## Guardrails (read before doing anything)

These are absolute. They protect the user's git state and harness files.
Canonical conventions: [no Co-Authored-By
trailer](../memory/conventions.md#no-co-authored-by-trailer), [stage explicit
paths](../memory/conventions.md#stage-explicit-paths), [the committed Claude
config](../memory/conventions.md#the-claude-config-is-committed) — they apply
here even though the rules are restated inline below (a command enforces its own
safety contract).

- **Never add a `Co-Authored-By:` trailer.** Not to the commit, not to the PR
  body. Ever. The user has asked for this explicitly.
- **Never stage `CLAUDE.md`, `.claude/**`, or memory files** unless the user
  said so in this turn. These are Claude harness files — they don't belong in
  the team's history. Stage only the code/docs the change is actually about.
- **Stage explicitly, never `git add -A`/`git add .`.** Blanket adds sweep in
  the files above and any stray local artifacts. List the paths you mean to
  commit so the staged set is auditable.
- **Don't force-push and don't touch other branches.** You move the current
  work onto a feature branch; you don't rewrite history that may be shared.

## Step 1 — Survey the change

```bash
git fetch origin master --quiet
git status --short
git diff origin/master...HEAD --stat
git diff origin/master...HEAD --name-only
git diff --stat            # unstaged/uncommitted work, if any
```

Read enough of the actual diff to write an honest summary. Note which files are
code/docs (stageable) and flag any harness files (see guardrails) so you exclude
them.

## Step 2 — Land the work on a feature branch

```bash
git branch --show-current
```

If you are on `master`, create and switch to a `<type>/<slug>` branch and move
the uncommitted work there (a plain `git switch -c` carries the working tree
with it — no stash needed):

```bash
git switch -c <type>/<slug>
```

`<type>` is one of `feat | fix | docs | test | ci | chore | release`. The slug
is a short kebab summary, e.g. `fix/supplier-refresh`, `feat/audit-log`,
`chore/green-ci`. If you are already on a feature branch, stay on it.

## Step 3 — Commit the code changes only

Stage the specific code/docs paths (never the excluded set), then commit with a
Conventional-Commit subject:

```bash
git add <path> <path> ...
git commit -m "<type>(<scope>): <imperative lower-case subject>"
```

- Scope is the area touched: `feat(frontend):`, `fix(models):`,
  `docs(system-overview):`, `test(dwh):`, `ci:`, `chore:`, `release:`.
- Subject is imperative and lower-case ("add audit-log read path", not "Added").
- One commit per PR is the norm here; split only if the change is genuinely two
  things.

## Step 4 — Push

```bash
git push -u origin <type>/<slug>
```

## Step 5 — Open the PR

Build the body from `.github/pull_request_template.md`:

- `## What` — a bullet per change, in plain language. End a bullet with
  `(Closes #N)` where it resolves an issue. A PR may close more than one.
- `## Not included` — optional; name follow-ups you deliberately left out so a
  reviewer doesn't flag them as gaps.
- `## Test` — exactly what you ran to gain confidence: `make check`,
  `pytest tests/...`, `tsc --noEmit`, `make smoke`. Be specific; "ran tests" is
  not a test note.

Write the body to a temp file (so the markdown survives shell quoting) and
create the PR. Keep the `--title` aligned with the commit subject.

```bash
cat > /tmp/pr-body.md <<'EOF'
## What

- ... (Closes #N)

## Test

- make check
- pytest tests/...
EOF

gh pr create --base master --title "<type>(<scope>): <subject>" --body-file /tmp/pr-body.md
```

Print the PR URL `gh` returns.

## Checklist

- [ ] No `Co-Authored-By:` trailer anywhere.
- [ ] No `CLAUDE.md` / `.claude/**` / memory files staged.
- [ ] On a `<type>/<slug>` branch, not `master`.
- [ ] Conventional-Commit subject, imperative and lower-case.
- [ ] PR body has `## What` and `## Test`; `Closes #N` present when an issue applies.
