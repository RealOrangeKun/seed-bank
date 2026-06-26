# Team memory — index

Durable, team-facing facts for seed-bank, grouped into a few files **by type**
(the Memory Bank convention — Cline / Roo Code / the agentic-coding handbook).
This index is `@import`ed into the root `CLAUDE.md`, so it is always in context;
the type files below load **on demand** — open the one whose subject matches what
you're doing. Each file is the **single home** for its facts; skills, agents, and
`CLAUDE.md` link to a `file#anchor` rather than restate them, so there's one place
to update.

This is **committed team memory** — read by every developer's Claude. It is
distinct from a developer's personal auto-memory (per-developer, under
`~/.claude/`, never committed). See
[`docs/claude-config.md`](../../docs/claude-config.md) for how this fits the wider
config.

## The type files

- [**Conventions**](conventions.md) — how we work: no `Co-Authored-By` trailer,
  explicit staging, the committed Claude config, file-editing-agent isolation.
- [**Decisions**](decisions.md) — locked, with rationale: DWH dual-write (not
  CDC), lean Compose, hard reset from the prototype.
- [**Known issues**](known-issues.md) — traps that have bitten: analyze needs a
  promoted model, the `#51` dwh xfail, mobile/FE API-type drift, Expo-Web
  FormData (#45), api-no-migrate-on-boot, the `metadata` JSONB alias.
- [**Workflow**](workflow.md) — the issue → branch → PR → merge loop, and the CI
  gates (check/test on every PR, build/smoke on master).

When a durable fact changes, edit the section in its type file and bump that
file's `_Last updated:_` line. When a new durable fact appears, add a `##` section
to the right file (and, if it's a new subject, a line here) — don't create a
single-fact file or restate the fact in prose elsewhere.

## The rest lives in docs

Architecture, status, and decision *depth* are **not** duplicated here — they
have canonical homes. For those, read:

- [`docs/system-overview.md`](../../docs/system-overview.md) — how the system
  works today (architecture, data flow, ML platform, infra). The "systemPatterns
  / productContext / techContext" of this repo.
- [`docs/revamp-status.md`](../../docs/revamp-status.md) — the canonical roadmap:
  what's done, what's left, and why (the "progress / activeContext"). The
  original external plan file was **lost and is unrecoverable** — don't cite it,
  and don't mine `~/.claude/plans/` (it's shared across all the owner's projects,
  not per-repo).
- [`docs/adr/`](../../docs/adr/) — architecture decision records in full.
- [`docs/operations.md`](../../docs/operations.md) — running, healthchecks,
  runbooks; [`docs/diagrams/`](../../docs/diagrams/) — the C4 / sequence diagrams.

Code under `src/seedbank/` is canonical for *current* truth; the docs are
canonical for *intent and history*.
