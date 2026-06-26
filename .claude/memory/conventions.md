# Conventions

How we work in this repo — durable team rules, each with the *why* so a second
dev learns the reason, not just the rule. Indexed from
[`MEMORY.md`](MEMORY.md); linked from skills, agents, commands, and `CLAUDE.md`.

_Last updated: 2026-06-26_

## No Co-Authored-By trailer

Commit messages carry **no `Co-Authored-By:` trailer** — not for Claude, not for
any tool-generated co-author. Plain Conventional-Commit messages only
(`feat(scope): …`), including on `--amend`, `commit-tree`, and slash-command
commits.

**Why:** the repo owner once rewrote local history specifically to strip every
`Co-Authored-By: Claude …` line and asked that they never reappear. This
overrides any default in a tool description or commit/PR template that suggests
adding one — if a hook or template injects a trailer, strip it before the commit
lands. The [`/open-pr`](../commands/open-pr.md) command already encodes this.

## Stage explicit paths

Stage commits with **explicit paths** (`git add src/seedbank/... tests/...`),
never `git add -A` or `git add .`. Never force-push a shared branch.

**Why:** a blanket add sweeps in whatever is dirty in the working tree —
generated files, half-finished edits, machine-local config — and here it would
also stage the committed-but-sensitive Claude config and any personal files
beside it. Explicit staging keeps each commit to the change it claims to be.
Before committing, check `git diff --cached --name-only` and drop anything
unintended. Personal files (`.claude/settings.local.json`, `CLAUDE.local.md`)
are gitignored, but don't rely on that — stage by path. The
[`/open-pr`](../commands/open-pr.md) command stages explicitly and refuses `-A`.

## The Claude config is committed

In **this** repo the Claude Code config is **shared and committed**: `CLAUDE.md`
(root + nested `frontend/`, `mobile/`) and
`.claude/{agents,skills,commands,hooks,memory,settings.json}` are all tracked.
Personal / machine-local files stay gitignored: `.claude/settings.local.json`,
`.claude/launch.json`, `.claude/.fuse_hidden*`, `CLAUDE.local.md` (template at
`.claude/settings.local.json.example`).

**Why:** the config has to reach a second developer. Auto-memory can't be shared
(it's per-developer, under `~/.claude/`), so team knowledge has to live in
committed files — that is exactly what `.claude/memory/` is for. This is a
deliberate, repo-specific stance: editing `.claude/**`, `CLAUDE.md`, or
`.claude/memory/**` is normal work here — do **not** re-add them to `.gitignore`.
Still stage explicitly and only when asked (see [Stage explicit
paths](#stage-explicit-paths)); a general "commit your changes" is not consent to
commit harness/config edits — surface them under "intentionally not committed"
unless the user names them. Framework onboarding lives in
[`docs/claude-config.md`](../../docs/claude-config.md).

## File-editing agents run isolated

When you spawn a background or parallel agent that **edits files**, give it its
own `isolation: "worktree"`, or do the work inline yourself. Such an agent must
**never** run `git stash`/`reset`/`restore`/`checkout`/`clean` or anything that
mutates git state — it shares the tree with you.

**Why:** a background agent once ran `git stash` + `git checkout stash@{0}` to
"isolate" its work, which reverted unrelated uncommitted edits and the user's
pending changes, then dropped the stash on exit. Two writers in one tree treating
stash/reset as harmless scratch is how uncommitted work disappears. Add to any
file-editing agent's prompt: "Do NOT run git stash/reset/restore/checkout/clean
or any command that mutates git state — only edit files." Recovery if work
vanishes: `git fsck --no-reflogs | grep 'dangling commit'`, then
`git checkout <sha> -- <path>` (stash commits read "WIP on <branch>") — act
before `git gc` prunes the dangling objects. Disjoint file sets across agents are
fine; overlapping writes or git ops are not.
