# 03 — API Components

The internal layering of the `api` container. Mirrors pillar 2 of
`CLAUDE.md`: **routers → services → repositories → ORM**, with no
cross-cuts.

## Diagram

```mermaid
flowchart TB
    Client[["HTTP client"]]

    subgraph API["api container (FastAPI)"]
        direction TB

        subgraph MW["Middleware<br/>core/, api/middleware.py, api/errors.py"]
            REQID["request_id"]
            LOG["structured logging"]
            CORS["CORS"]
            RL["rate limiter"]
            EXH["problem-details<br/>exception handler"]
        end

        subgraph V1["Routers — src/seedbank/api/v1/"]
            R_AUTH["auth.py<br/>POST /auth/login<br/>POST /auth/refresh<br/>POST /auth/oauth/{provider}"]
            R_USERS["users.py"]
            R_MODELS["models.py"]
            R_ANALYZE["analyze.py<br/>POST /analyze"]
            R_BATCH["batches.py<br/>GET /batches<br/>GET /batches/{id}"]
        end

        DEPS["api/deps.py<br/>current_user, require_role,<br/>db, redis, minio, repos, services"]

        subgraph SVC["Services — src/seedbank/services/"]
            S_AUTH["AuthService"]
            S_REG["ModelRegistryService"]
            S_TR["ModelResolver"]
            S_AN["AnalysisService"]
            S_BAT["BatchService"]
        end

        subgraph REPO["Repositories — src/seedbank/infrastructure/db/repositories/"]
            R_USER["UserRepository"]
            R_OAUTH["OAuthAccountRepository"]
            R_RT["RefreshTokenRepository"]
            R_MA["ModelArtifactRepository"]
            R_SUP["SupplierRepository"]
            R_SB["ScanBatchRepository"]
            R_SI["ScanImageRepository"]
            R_INF["InferenceRepository"]
            R_SD["SeedDetectionRepository"]
        end

        subgraph INFRA["Infrastructure adapters"]
            ML["infrastructure/ml<br/>(see view 04)"]
            STO["storage/MinioStorage"]
            CACHE["cache/Redis"]
            OAUTH["oauth/google.py"]
            ANA["analytics/clickhouse"]
        end

        ORM[("SQLAlchemy 2.0 AsyncSession<br/>infrastructure/db/models.py")]
    end

    Client --> MW
    MW --> V1
    V1 --> DEPS
    DEPS --> SVC

    R_AUTH --> S_AUTH
    R_USERS --> S_AUTH
    R_MODELS --> S_REG
    R_ANALYZE --> S_AN
    R_BATCH --> S_BAT

    S_AUTH --> R_USER
    S_AUTH --> R_OAUTH
    S_AUTH --> R_RT
    S_AUTH --> OAUTH

    S_REG --> R_MA
    S_TR --> R_MA
    S_AN --> R_SB
    S_AN --> R_SI
    S_AN --> STO
    S_AN -. "send_task" .-> CACHE
    S_BAT --> R_SB
    S_BAT --> R_SI

    R_USER --> ORM
    R_OAUTH --> ORM
    R_RT --> ORM
    R_MA --> ORM
    R_SUP --> ORM
    R_SB --> ORM
    R_SI --> ORM
    R_INF --> ORM
    R_SD --> ORM
```

## Layering rules (enforced by review, not lint)

1. **Routers** never import SQLAlchemy. They parse request → call a
   service → wrap the result in `Envelope` or `Page` → return.
2. **Services** never import FastAPI. They take primitives (UUIDs,
   bytes, dataclasses) and raise domain exceptions
   (`ValidationError`, `ForbiddenError`, `NotFoundError`,
   `ExternalServiceError`).
3. **Repositories** never embed business rules. One method = one query
   or one persistence intent.
4. **Domain entities** (`src/seedbank/domain/`) are framework-free
   dataclasses. They cannot import SQLAlchemy, FastAPI, or Pydantic.

## Error mapping

`api/errors.py` registers handlers that turn every domain exception
into an RFC 9457 Problem Details response with the right status code:

| Domain exception | HTTP status | `code` field |
|---|---|---|
| `ValidationError` | 422 | `validation_error` |
| `AuthError` | 401 | `auth_error` |
| `ForbiddenError` | 403 | `forbidden` |
| `NotFoundError` | 404 | `not_found` |
| `ConflictError` | 409 | `conflict` |
| `RateLimitError` | 429 | `rate_limited` |
| `ExternalServiceError` | 502/503 | `external_service_error` |

Every response — success or failure — is JSON. No HTML error pages.
