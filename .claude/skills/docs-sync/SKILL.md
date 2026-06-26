---
name: docs-sync
description: Keep docs/ and the Mermaid C4 diagrams current after a schema or architecture change. Use when you add a table, a router, a worker task, a queue, an image target, or change the analyze/batch/auth/ML flows — anything the diagrams under docs/diagrams/ or the prose in docs/system-overview.md and docs/revamp-status.md describe.
---

# Sync docs and diagrams to a change

## Purpose

The diagrams and overview docs are how a new engineer (or an agent) reads the
system cold. They go stale the moment code lands and the doc doesn't — and a
wrong diagram is worse than no diagram, because people trust it. This skill
makes the doc update a deliberate, **scoped** part of the change: touch only the
diagram(s) and prose the change actually affects, leave the rest alone.

## When to use

After any change that alters something a doc describes: a new/removed table or
column, a new router or endpoint surface, a new worker task or queue, a changed
analyze/batch/auth/ML flow, a new image target or deployment topology. If the
change is invisible at the architecture level (a refactor inside one service,
a test, a lint fix), the docs don't move.

## Steps

### 1. Map the change to the artifact(s) it touches

The diagrams live in `docs/diagrams/*.md` as fenced Mermaid. Each owns a slice;
match your change to the smallest set:

| You changed… | Update |
|---|---|
| A table / column / FK / index | `05-db-erd.md` |
| A v1 router or endpoint surface | `03-api-components.md` |
| A worker task or queue | `04-worker-components.md` |
| The analyze request flow | `06-analyze-sequence.md` |
| Batch lifecycle / states / transitions | `07-batch-state-machine.md` |
| Login / token / refresh / OAuth flow | `08-auth-sequence.md` |
| Model registry / promotion / traffic / experiments | `09-ml-platform.md` |
| A container, image target, or service | `02-containers.md`, `10-deployment.md` |
| Top-level actors / external systems | `01-system-context.md` |
| A durable team fact — a gotcha learned, a CI/workflow change, a locked decision | the section in the matching `.claude/memory/` type file (`conventions`/`decisions`/`known-issues`/`workflow`) — bump that file's `_Last updated:_` line |

A single change can hit more than one (e.g. a new analyze field that comes from
a new column → `05-db-erd.md` **and** possibly `06-analyze-sequence.md`). Pick
the set, not the whole folder.

### 2. Regenerate just that Mermaid

Open the matched file(s) and edit the Mermaid block in place — add the node,
edge, entity, or transition that changed; rename or remove what's gone. Keep the
existing notation and naming (the ERD uses the real table names; the sequence
diagrams use the real participant names). Don't reflow or restyle unrelated
parts of the diagram — a clean diff is reviewable, a full redraw is not.

### 3. Update the prose

Two docs carry the narrative; reconcile the ones the change touches:

- `docs/system-overview.md` — the comprehensive map. Update the section that
  describes the changed component (and bump its "Last updated" line).
- `docs/revamp-status.md` — the roadmap/status reconstruction. If the change
  completes or moves a tracked item, reflect it here.

Match the existing tone; add the *why* of the change, not just the *what*.

### 3b. Check the team memory files

The committed `.claude/memory/` type files (`conventions.md`, `decisions.md`,
`known-issues.md`, `workflow.md`) are the single home for durable team facts. If
your change invalidates one — a decision reversed, a gotcha fixed, a CI gate
changed — edit that fact's `##` section and bump the file's `_Last updated:_`
line. Don't restate the fact in prose elsewhere; link to its `file#anchor`. A
stale fact here is exactly the drift this layer exists to prevent. If a new
durable fact has no section yet, add a `##` section to the right type file (and a
line to `.claude/memory/MEMORY.md` if it's a new subject) — don't create a
single-fact file. See `docs/claude-config.md` for the file convention.

### 4. Sanity-check the Mermaid renders

A broken diagram block silently fails to render. Eyeball the fence syntax (the
`erDiagram` / `sequenceDiagram` / `stateDiagram-v2` header, balanced brackets).
If you have a Mermaid linter or a preview to hand, use it; otherwise read the
block back end to end.

## Conventions

- **Scope discipline: touch only what changed.** This is the core rule — no
  blanket redraw. The reviewer should see exactly which node/edge/row moved.
- The diagrams are **backend-centric today.** Adding the frontend and mobile
  clients to `01-system-context.md` and `02-containers.md` is a known,
  deliberate follow-up — don't fold it into an unrelated change, but note it if
  your change makes the omission newly misleading.
- Diagram source is Mermaid in Markdown fences under `docs/diagrams/`. There is
  no build step that regenerates them — they are edited by hand.
- The ERD and sequence diagrams use **real** names (tables, columns,
  participants, queues). Keep them faithful to the code; a diagram that invents
  a name is a trap.

## Gotchas

- **Don't do a blanket redraw.** Rewriting a whole diagram to change one edge
  buries the real change in noise and invites copy-paste errors elsewhere in
  the figure. Edit surgically.
- **A change can be doc-invisible.** Not everything needs a diagram edit. An
  internal refactor with no architectural footprint should leave `docs/`
  untouched — don't manufacture churn.
- **Stale prose outlives stale diagrams.** It's easy to fix the picture and
  forget the paragraph (and the "Last updated" date) in `system-overview.md`.
  Update both, or the doc contradicts itself.
- **Frontend/mobile aren't in 01/02 yet.** If you're documenting a
  cross-surface change, note that the client containers are still a pending
  addition rather than silently half-adding them.

## Checklist

- [ ] Mapped the change to the minimal set of `docs/diagrams/*.md` it affects.
- [ ] Edited those Mermaid block(s) surgically — added/renamed/removed only what
      changed, no blanket redraw.
- [ ] Updated the relevant section of `docs/system-overview.md` (and its
      "Last updated" line).
- [ ] Reflected any roadmap/status movement in `docs/revamp-status.md`.
- [ ] Updated the affected `.claude/memory/` type-file section and bumped that
      file's `_Last updated:_` line; added a `MEMORY.md` index line if the fact is
      a new subject.
- [ ] Eyeballed the edited Mermaid fences for syntax so they still render.
- [ ] Left unrelated diagrams and the pending frontend/mobile 01/02 follow-up
      alone.
