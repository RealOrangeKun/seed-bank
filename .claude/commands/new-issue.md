---
description: Scaffold a GitHub issue in the house style (Bug with Root cause/Fix, or task with What/Why/Acceptance) and open it with gh
allowed-tools: Bash, Read
---

# /new-issue

Write an issue the way the team writes them, then open it with `gh`. A good
issue is actionable on its own: a reviewer should know what to do and how to
know it's done without asking you.

Argument: a short description of the problem or the request. Decide which of the
two shapes fits.

## Pick the shape

- **Bug** — something behaves wrong. Title prefix `Bug:`. The body leads with a
  `**Root cause**` section (what actually causes it — not just the symptom) and
  a `**Fix**` section (the change that resolves it). This split is what makes
  our bugs reviewable; see issue #50 for the canonical form.
- **Task / feature** — new behavior or an endpoint we want. Title prefix
  `feat:`. The body states the desired behavior, why it matters, and how we'll
  know it's done.

Only diagnose a root cause you can actually support — read the relevant code
first. A guessed root cause is worse than none because it sends the fixer down
the wrong path.

## Bug body

```markdown
<one-sentence symptom: what fails, where, and the observable error>

**Root cause:** <the underlying reason — the layer/file/condition that produces
the symptom, not a restatement of the symptom>

**Fix:** <the concrete change that resolves it — file/function and what to do>
```

## Task body

```markdown
## What
<the desired endpoint/behavior, concretely — method + path, or the user-visible flow>

## Why
<the value: what it unblocks or the defect it closes>

## Acceptance
- [ ] <observable, checkable condition>
- [ ] <test that must exist: unit / integration / e2e per CLAUDE.md>
```

## Open it

Write the body to a temp file so markdown survives shell quoting, then create
the issue with the prefixed title. Apply `--label bug` for bugs.

```bash
cd /mnt/shared_data/FCAI/GP/project/seed-bank/
cat > /tmp/issue-body.md <<'EOF'
<body from the matching shape above>
EOF

# Bug:
gh issue create --title "Bug: <short summary>" --label bug --body-file /tmp/issue-body.md
# Task:
gh issue create --title "feat: <short summary>" --body-file /tmp/issue-body.md
```

Print the issue URL `gh` returns.

## Checklist

- [ ] Title carries the right prefix (`Bug:` / `feat:`).
- [ ] Bug bodies have both `**Root cause**` and `**Fix**`.
- [ ] Task bodies have `## What`, `## Why`, `## Acceptance` with checkable items.
- [ ] Any root cause stated is backed by reading the code, not guessed.
