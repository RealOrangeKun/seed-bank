# 01 — System Context

The outermost view: people and external systems that interact with
seed-bank. Useful for onboarding ("what does this thing do, and to
whom?") and for scoping discussions ("is this in or out of our
boundary?").

## Diagram

```mermaid
flowchart LR
    %% Actors
    EU([End user<br/>uploads seed images])
    AID([AI developer<br/>registers/promotes models,<br/>runs experiments])
    AD([Admin<br/>operates the platform])

    %% System boundary
    subgraph SB["Seed-Bank platform"]
        API[(FastAPI service<br/>+ Celery workers)]
    end

    %% External systems
    GOO[Google OAuth]
    RB[Roboflow Inference API<br/>optional backend]
    SE[Sentry<br/>error tracking, optional]

    %% Edges
    EU -- "POST /analyze<br/>GET /batches/{id}" --> API
    AID -- "POST /models, PATCH /models/{id}<br/>POST /experiments" --> API
    AD  -- "PATCH /users/{id}" --> API

    API -- "OIDC code flow" --> GOO
    API -. "POST inference (per image)" .-> RB
    API -. "events, errors" .-> SE
```

## Notes

- All three actor classes (`end_user`, `ai_developer`, `admin`) hit the
  same HTTP surface; what changes is the RBAC scope. See
  [08 — Auth sequences](08-auth-sequence.md).
- Roboflow is one of three model backends (`torch_local`, `roboflow`,
  `yolo`). The system functions fully without it; the dashed edge is
  optional.
- Sentry is opt-in via `SENTRY_DSN`. Empty in dev.
- ML training happens *outside* this system — only the resulting
  weights and metrics are imported via `scripts/register_model.py` and
  the `POST /api/v1/models` endpoint.
