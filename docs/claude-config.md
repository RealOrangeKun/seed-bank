# How we use Claude Code in this repo

This is the team guide to the Claude Code setup that ships with seed-bank.
Read it once before you touch anything under `.claude/` or any `CLAUDE.md`, so
your changes land where teammates expect them and survive a fresh checkout.

> This describes the **live** setup — every agent, skill, command, hook, and
> memory file named below exists on disk and is committed. When you add or change
> one, update this doc to match.

---

## The framework (naming)

There is no single official umbrella name for "the Claude Code config." It is a
set of independent pieces, each with its own loading rules:

- **CLAUDE.md** — project memory, always loaded into context.
- **Agent Skills** — procedures Claude loads on demand or you invoke by name.
- **Subagents** — separate agents with their own context window and tool set.
- **Slash commands** — explicit actions you type (`/check`).
- **Hooks** — deterministic scripts the harness runs on lifecycle events.
- **MCP servers** — external tool/data providers wired in over the MCP protocol.

The unit that **bundles and distributes** these for a team is a **Plugin**,
shared through a **Marketplace**. We don't need that yet. For one repo the
simpler standard is enough: a **committed `.claude/` directory plus nested
`CLAUDE.md` files**, checked into git so every clone gets the same setup. If we
later want to share this across repos, it promotes cleanly into a plugin — same
files, different packaging.

---

## What lives where

| Location | Kind | Loading | What it holds |
|---|---|---|---|
| `CLAUDE.md` (root) | Project memory | Always loaded | Stack pillars, repo layout, golden paths, pointers into `docs/` |
| `frontend/CLAUDE.md` | Nested memory | Loads when you work under `frontend/` | React SPA conventions |
| `mobile/CLAUDE.md` | Nested memory | Loads when you work under `mobile/` | Mobile-app conventions |
| `.claude/memory/` (`MEMORY.md` + type files) | Team memory | Index `@import`ed (always loaded); type files read on demand | Durable team facts grouped by type — `conventions`, `decisions`, `known-issues`, `workflow`; the single home other files link to |
| `.claude/agents/*.md` | Subagents | Invoked by name or auto-delegated | Isolated-context roles: `backend-engineer`, `db-architect`, `ml-platform`, `security-reviewer`, `test-writer`, `devops-helper`, `frontend-engineer`, `mobile-engineer` |
| `.claude/skills/<name>/SKILL.md` | Agent Skills | Auto-loaded by description, or you invoke | Procedures: `backend-dev`, `add-endpoint`, `add-model`, `db-migration`, `run-experiment`, `incident-response`, `testing`, `frontend-dev`, `mobile-dev`, `api-contract`, `write-adr`, `docs-sync` |
| `.claude/commands/*.md` | Slash commands | You type `/<name>` | Explicit actions: `check`, `new-migration`, `scaffold-feature`, `grade-pr`, `open-pr`, `new-issue` |
| `.claude/hooks/*.sh` | Hooks | Fired by the harness on events | Deterministic must-happens: format on edit, typecheck changed files, guard unsafe bash, inject stack reminders |

Nested `CLAUDE.md` keeps the root file small: frontend/mobile rules only cost
context when you're actually in those trees. Subagents exist so a focused job
(a security pass, a test write) runs in its **own** context and can't pollute or
be polluted by the main thread, and so we can hand each role a narrower tool set.

---

## Team memory (the typed files)

`.claude/memory/` follows the **Memory Bank** convention (Cline / Roo Code / the
agentic-coding handbook): a few committed files grouped **by type**, the single
home for durable facts that don't belong in always-on prose. The files:

- `conventions.md` — team working rules, each with the *why*.
- `decisions.md` — locked architectural decisions; each a statement + why + a link
  to its `docs/`/ADR home (thin pointers, not copies).
- `known-issues.md` — gotchas and bugs with a known cause and workaround.
- `workflow.md` — the issue → PR → merge loop and the CI gates.

CLAUDE.md, skills, and agents **link** to a `file#anchor` instead of restating a
fact, so there is one place to update when it changes — the same anti-staleness
move we make for the docs.

How it loads:

- `MEMORY.md` is the index (one line per type file + a pointer block to the docs
  that own architecture/status). CLAUDE.md `@import`s it, so the index is always
  in context — cheap and scannable.
- The type files are plain links, **not** `@`-imports, so they load **on demand**.
  Committed files get no automatic relevance-recall (that's the trade vs. personal
  auto-memory) — so a hard, must-always-hold rule *also* stays inline in CLAUDE.md
  as an enforceable rule; the type file carries the *why* and the depth.
- **Agents run in isolated context** and don't receive the `@import`ed index, so
  agent files keep the essential fact inline and point by explicit path+anchor
  (`.claude/memory/<file>.md#<anchor>`).

File convention — no YAML frontmatter, no wikilinks; match the repo's doc style.
Each file opens with a one-line purpose + a `_Last updated: <date>_` line (what
`docs-sync` checks for staleness); each fact is a `##` section so its heading is a
stable anchor; cross-references are plain markdown links. Architecture, status,
and decision *depth* are **not** duplicated — `MEMORY.md` points to
`docs/system-overview.md`, `docs/revamp-status.md`, and `docs/adr/` for those.

> We deliberately moved off the atomic-note (Zettelkasten) layout the personal
> auto-memory uses: that pattern earns its keep through the harness's automatic
> relevance-recall, which **committed** files don't get — so the atom split was
> all cost (many files, frontmatter, an index, backlinks) and no benefit here.

This is **not** a developer's personal auto-memory (next section): team memory is
committed and read by everyone's Claude; auto-memory is personal, lives under
`~/.claude/`, and cannot be shared.

---

## Committed vs personal (critical)

| Commit (shared, team source of truth) | Do NOT commit (personal, machine-local) |
|---|---|
| `CLAUDE.md` (root and all nested) | `.claude/settings.local.json` |
| `.claude/agents/`, `.claude/skills/`, `.claude/commands/`, `.claude/hooks/`, `.claude/memory/` | `CLAUDE.local.md` |
| `.claude/settings.json` | `~/.claude/.../memory/` (auto-memory) |

The split is about reach. `settings.json` is the team's harness config — hooks,
shared permissions — so everyone gets the same guardrails. `settings.local.json`
and `CLAUDE.local.md` are your machine: local paths, personal permission
allowances, experiments you haven't blessed for the team. They stay gitignored.

**Auto-memory is per-developer and cannot be shared.** It lives outside the repo
under your home directory and records *your* sessions. Anything a teammate needs
to know — a convention, a gotcha, a decision — has to move into a committed file:
a `.claude/memory/` type file (the natural home for a convention/decision/gotcha),
`CLAUDE.md`, a skill, or a `docs/adr/` entry. If it only lives in your memory, it
doesn't exist for anyone else.

> Repo note: `.gitignore` is set up to share this config. It tracks `CLAUDE.md`
> (root + nested), `.claude/{agents,skills,commands,hooks}`, and
> `.claude/settings.json`, while keeping the personal files out —
> `.claude/settings.local.json`, `.claude/.fuse_hidden*`, `.claude/launch.json`,
> and `CLAUDE.local.md`. Clone the repo and the team config is there; copy
> `.claude/settings.local.json.example` → `settings.local.json` for your own
> machine-local overrides.

---

## When to use which

A quick decision guide — match the shape of the thing you're adding:

- A **slim, always-on fact or pointer** (a stack pillar, a "where to look") →
  **CLAUDE.md**.
- A **durable fact with rationale or history** (a convention, a locked decision, a
  gotcha) → a `##` section in the matching **`.claude/memory/` type file**,
  indexed by `MEMORY.md`. Keep an
  always-must-hold rule *also* summarized in CLAUDE.md so it's enforced even
  unread.
- A **multi-step procedure** (how to add a model, run an experiment) → **skill**.
- A task needing **isolated context or a restricted tool set** (review a diff,
  write tests without touching prod code) → **subagent**.
- A **deterministic action that must always happen** (format on save, block a
  push to main) → **hook**. Claude can forget; a hook can't.
- An **explicit action you trigger by typing** → **slash command**.

If two fit, prefer the lighter one: a fact over a skill, a skill over an agent.

---

## How to add one

**New skill** — create `.claude/skills/<name>/SKILL.md` with `name` and
`description` frontmatter. The `description` is the trigger: it's how Claude
decides to auto-load the skill, so make it concrete — name the surface and the
verbs ("Use when adding tests…", not "testing stuff"). Body follows the skeleton
in the voice guide below.

**New agent** — create `.claude/agents/<name>.md` with `name`, `description`,
and `tools` frontmatter. `description` drives delegation; `tools` is the
comma-list the agent is allowed to call — give it the minimum it needs.

**New command** — create `.claude/commands/<name>.md` with `description` and
`allowed-tools` frontmatter.

**New memory fact** — add a `##` section to the right `.claude/memory/` type file
(`conventions`/`decisions`/`known-issues`/`workflow`), write the fact (with the
*why*, plus a "how to apply" for a convention/decision), bump that file's
`_Last updated:_` line, and add a `MEMORY.md` index line if it's a new subject.
Then link to its `file#anchor` from the skills/agents/`CLAUDE.md` that used to
restate the fact, rather than duplicating. Don't create a single-fact file.

Whatever you add, restyle it to the voice guide before committing.

---

## Voice guide

Every `CLAUDE.md`, agent, skill, and command in this repo follows the same five
rules so the config reads like one team wrote it:

1. **Neutral, teaching, rationale-first.** Keep the rule, add the *why*, so a
   second dev learns instead of just obeys.
2. **No single-author persona.** An agent file is role + scope + hard rules +
   output format — not a performance. Write "Scope: … Rules: …", not "You are a
   senior X who refuses…".
3. **Terse but complete.** No filler, no trailing summaries. Depth belongs in
   skills, not prose padding.
4. **Consistent skeletons.** Skill `SKILL.md` body: `## Purpose` / `## When to
   use` / `## Steps` / `## Conventions` / `## Gotchas` / `## Checklist`. Agent
   body: `## Scope` / `## Hard rules` / `## Output`.
5. **Keep `CLAUDE.md` files under 200 lines.** It's always-loaded context;
   every line costs every session. Link out to `docs/` for deep dives.

Address the reader as a teammate ("you"/"we"), gender-neutral. This is a
multi-dev repo, so write for the newcomer who just cloned it.

---

## Verifying config changes

- **Skills hot-reload in-session** — edit a `SKILL.md` and it's picked up without
  a restart.
- **Agents, hooks, and `settings.json` reload at session start** — restart the
  session (or start a fresh one) after editing them, or your change won't apply.
- **Validate `settings.json` before you trust it:**
  `python -c "import json; json.load(open('.claude/settings.json'))"`.
  A malformed settings file can silently drop your hooks and permissions.
- **Run `/check` before opening a PR.** Same gate CI runs (ruff format, ruff
  check, mypy, fast unit subset). Green locally means green in CI.
