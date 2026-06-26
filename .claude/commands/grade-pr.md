---
description: Run backend-engineer, security-reviewer, test-writer (and frontend-/mobile-engineer when the diff touches those dirs) on the current diff and produce a consolidated grade
allowed-tools: Bash, Read, Glob, Grep, Agent
---

# /grade-pr

Run the specialist subagents that match what the diff touches, in parallel, and
fold their findings into one grade. The backend trio always runs; the
client-side reviewers run only when the diff actually touches their surface, so a
backend-only PR isn't graded against frontend rules it can't violate.

## Step 1 — Capture the diff and decide who reviews

```bash
cd /mnt/shared_data/FCAI/GP/project/seed-bank/
git fetch origin master --quiet
git diff origin/master...HEAD --stat
git diff origin/master...HEAD --name-only
```

If there is no diff, tell the user and stop.

From the `--name-only` list, decide the reviewer set:
- **Always:** `backend-engineer`, `security-reviewer`, `test-writer`.
- **Add `frontend-engineer`** if any changed path starts with `frontend/`.
- **Add `mobile-engineer`** if any changed path starts with `mobile/`.

A change to a Pydantic schema in `src/seedbank/schemas/` is a contract change the
clients consume — if the diff touches schemas *and* `frontend/` or `mobile/`, make
sure the matching client reviewer checks that the generated types / API layer were
regenerated (see the `api-contract` skill).

Then capture the full diff for the agents:

```bash
git diff origin/master...HEAD
```

## Step 2 — Launch the selected agents in parallel

Put all the calls in a single message (one Agent tool call per selected agent).
Hand each agent the diff (or just the touched paths — they have their own tools)
plus the relevant `CLAUDE.md` context.

1. **`backend-engineer`** — layered-architecture violations, async correctness
   (no sync DB in request paths), Pydantic at the edges, error handling
   (`DomainError`, never `HTTPException` in services), structured logging, config
   rules. Output in its Blockers / Should-fix / Nits format.
2. **`security-reviewer`** — OWASP, auth/RBAC, secrets, injection, dependencies.
   Output in its Critical / High / Medium / Informational format.
3. **`test-writer`** — test-pyramid coverage: are unit/integration/e2e tests at
   the right layers, are negative tests present, is coverage on the touched
   modules adequate?
4. **`frontend-engineer`** *(only if `frontend/` changed)* — review the React SPA
   diff for its own conventions and for drift against the backend contract.
5. **`mobile-engineer`** *(only if `mobile/` changed)* — review the Expo / React
   Native diff for its conventions and contract drift.

If a selected client reviewer's agent file does not exist yet, note that inline in
the report (so the gap is visible) rather than silently skipping the surface.

## Step 3 — Aggregate

One Markdown report. Keep the consolidated Blockers / Should-fix / Nits grade
regardless of how many agents ran:

```
# /grade-pr — <branch> vs master (<N> files changed)
# Reviewers: backend-engineer, security-reviewer, test-writer[, frontend-engineer][, mobile-engineer]

## Verdict: READY / CHANGES REQUESTED / NOT READY

## Blockers (must fix before merge)
- [security-reviewer] ...
- [backend-engineer] ...
- [frontend-engineer] ...

## Should fix before merge
- [test-writer] ...
- [mobile-engineer] ...

## Nits / suggestions
- ...

## Coverage delta
- (from test-writer)
```

Verdict logic:
- **NOT READY** if any Critical security finding or any Blocker from any engineer.
- **CHANGES REQUESTED** if any High security finding, missing negative tests, or any Should-fix.
- **READY** otherwise.

Tag every line with the agent that raised it, so the developer can weigh it.

## Don't do

- Don't summarize the diff itself — the user can read `git diff`. Produce the grade.
- Don't second-guess the agents' findings — surface them all and let the developer decide.
- Don't run a client reviewer when its directory wasn't touched — it has nothing to grade.
