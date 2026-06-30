---
name: write-adr
description: Author an Architecture Decision Record in docs/adr/ for the seed-bank repo. Use when a decision changes the architecture, locks a tradeoff, or needs a durable rationale a future teammate can pick up — e.g. choosing a queue, restructuring a tier, or scoping a phased overhaul.
---

# Write an ADR

## Purpose

An ADR captures *why* a decision was made, not just what we did. Code shows the
what; the ADR preserves the context and the rejected alternatives so a teammate
six months out doesn't relitigate a settled tradeoff or undo it without knowing
the cost. We keep them in `docs/adr/` as zero-padded, numbered, immutable-ish
records.

## When to use

- A decision shapes the architecture or crosses a stack pillar in `CLAUDE.md`
  (async, layering, Pydantic-at-edges, config-from-env, traceability).
- A tradeoff is locked and you want it to stay locked (queue choice, auth model,
  DWH approach, a phased overhaul plan).
- You're superseding an earlier decision — write a new ADR that references the
  old one rather than editing history.

Skip it for routine changes a PR description already explains. An ADR is for
decisions, not for every diff.

## Steps

1. Find the next number — list `docs/adr/` and take the highest `NNNN` + 1,
   zero-padded to four digits:

   ```bash
   ls docs/adr/
   ```

   `0001-frontend-backend-overhaul.md` exists, so the next is `0002`.

2. Create `docs/adr/NNNN-<slug>.md`. The slug is a short kebab summary of the
   decision (`0002-celery-queue-topology.md`).

3. Use the structure below — it mirrors
   `docs/adr/0001-frontend-backend-overhaul.md`, the template for shape and
   depth. Fill every section; an empty "Alternatives considered" is a smell
   (it usually means the decision wasn't actually weighed).

   ```markdown
   # ADR NNNN — <decision title>

   - **Status:** Proposed | Accepted | Superseded by ADR-XXXX
   - **Date:** YYYY-MM-DD
   - **Deciders:** <who signed off>
   - **Supersedes / relates to:** <links to prior ADRs or docs, if any>

   ## Context

   The forces at play: the problem, the constraints, what's true today. Enough
   that a newcomer understands the decision without prior context.

   ## Decision

   What we will do, stated plainly. This is the load-bearing section.

   ## Consequences

   What becomes easier and what becomes harder. Name the new constraints this
   imposes and any follow-up work it creates — positive and negative both.

   ## Alternatives considered

   Each option we weighed and why we did not pick it. This is what stops the
   decision from being relitigated.
   ```

4. Set **Status** honestly. `Proposed` until it's agreed; `Accepted` once it
   is. When a later ADR overrides this one, change the status to
   `Superseded by ADR-XXXX` rather than deleting the file — the trail matters.

5. Link related work: the overall roadmap (`docs/revamp-status.md`), prior ADRs,
   and any issue/PR that implements the decision.

## Conventions

- Numbers are sequential and zero-padded (`0001`, `0002`, …). Never reuse one.
- One decision per ADR. If you're deciding two things, write two files.
- Past decisions are immutable in spirit: correct typos, but record a *change*
  of decision as a new ADR that supersedes the old, not an in-place rewrite.
- Write for a teammate who wasn't in the room. Spell out tradeoffs and the
  losing options, not just the winner.

## Gotchas

- Don't let the ADR drift from reality. ADR 0001 carries a dated "Status update"
  section reconciling the plan against `master` — do the same when an accepted
  ADR is only partly implemented, rather than leaving it silently stale.
- Status and number are the two fields people skim first; get them right.
- An ADR is rationale, not a runbook. Operational steps belong in `docs/` or a
  skill; keep the ADR about the decision and its why.

## Checklist

- [ ] Filename is `docs/adr/NNNN-<slug>.md` with the next zero-padded number.
- [ ] Has Status, Date, Deciders, and links to related ADRs/docs.
- [ ] Context / Decision / Consequences / Alternatives considered all filled.
- [ ] Exactly one decision; superseded predecessors are linked, not deleted.
- [ ] Status reflects reality (Proposed vs Accepted vs Superseded).
