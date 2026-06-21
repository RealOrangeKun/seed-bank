# Seed-Bank — System Diagrams

Mermaid diagrams describing the seed-bank platform at every level. Renders
natively on GitHub. Each file is a single view; together they form a
zoom-in tour from "what is this system" down to "how does one analyze
request flow through the code".

The diagrams are kept close to the code on purpose: when a router, a
service, or a container moves, the matching diagram moves with it.
Anything you see in a diagram exists in the repo today (or is gated
behind a profile, e.g. the GPU worker).

## Index

| # | View | What it answers |
|---|---|---|
| 01 | [System context](01-system-context.md) | Who uses seed-bank, what does it talk to outside its own walls? |
| 02 | [Containers (compose stack)](02-containers.md) | Which processes run, on which ports, with what dependencies? |
| 03 | [API components](03-api-components.md) | How is the FastAPI app layered (router → service → repo → ORM)? |
| 04 | [Worker components](04-worker-components.md) | How does the Celery worker turn one image into one inference? |
| 05 | [Database ERD](05-db-erd.md) | What tables exist and how do they reference each other? |
| 06 | [Analyze request sequence](06-analyze-sequence.md) | End-to-end timing for `POST /analyze` → polled completion. |
| 07 | [Batch state machine](07-batch-state-machine.md) | What states does `scan_batch.status` transition through, and why? |
| 08 | [Auth sequences](08-auth-sequence.md) | Local login, refresh-token rotation, OAuth, API-key. |
| 09 | [ML platform](09-ml-platform.md) | Model lifecycle (registered → staging → production → archived) + traffic router + per-request override. |
| 10 | [Deployment](10-deployment.md) | The runtime topology: which container holds what, network, volumes, the GPU profile boundary. |

## Conventions

- **Sources of truth:** routers in `src/seedbank/api/v1/`, services in
  `src/seedbank/services/`, repositories in
  `src/seedbank/infrastructure/db/repositories/`, ORM in
  `src/seedbank/infrastructure/db/models.py`, compose stack in
  `compose.yaml`.
- **Boxes** are processes or modules. **Cylinders** are persistent
  stores. **Dashed arrows** are async / fire-and-forget (Celery
  dispatch, background metric writes).
- Names match the code exactly. If a diagram says `AnalysisService`,
  there is a class with that name at the obvious path.
