# 08 — Auth Sequences

Three auth flows live behind `/api/v1/auth/*` and one cross-cutting
"present a credential" path used by every other route. Routers in
`api/v1/auth.py`, service in `services/auth_service.py`, RBAC
enforcement in `api/deps.py`.

## Local login + refresh-token rotation

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant API as FastAPI
    participant Svc as AuthService
    participant UR as UserRepository
    participant RT as RefreshTokenRepository

    U->>API: POST /api/v1/auth/login<br/>{email, password}
    API->>Svc: login(email, password, ip, user_agent)
    Svc->>UR: get_by_email(email)
    Svc->>Svc: bcrypt.verify(password, hashed_password)
    alt invalid
        Svc-->>API: AuthError
        API-->>U: 401 Problem Details
    else valid
        Svc->>RT: insert(token_hash=sha256(rt), expires_at=+30d, ip, user_agent)
        Svc->>Svc: sign access JWT (exp=15m, role, scopes)
        Svc-->>API: TokenPair(access, refresh)
        API-->>U: 200 Envelope[TokenPair]
    end

    note over U,API: …time passes, access token expires…

    U->>API: POST /api/v1/auth/refresh<br/>{refresh_token}
    API->>Svc: rotate(refresh_token)
    Svc->>RT: get_by_hash(sha256(rt))
    alt revoked or expired
        Svc-->>API: AuthError
    else valid
        Svc->>RT: revoke(old_id, replaced_by_id=new_id)
        Svc->>RT: insert(new_token_hash, …)
        Svc->>Svc: sign new access JWT
        Svc-->>API: TokenPair(new_access, new_refresh)
    end
```

## OAuth (Google / GitHub)

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant Browser
    participant API as FastAPI<br/>/auth/oauth/{provider}
    participant P as Provider<br/>(Google/GitHub)
    participant Svc as AuthService
    participant OA as OAuthAccountRepository
    participant UR as UserRepository
    participant RT as RefreshTokenRepository

    U->>API: GET /auth/oauth/{provider}/start
    API-->>Browser: 302 → provider authorize URL<br/>(state, nonce)
    Browser->>P: authorize
    P-->>Browser: 302 → /auth/oauth/{provider}/callback?code=…&state=…
    Browser->>API: GET callback?code=…
    API->>Svc: complete_oauth(provider, code, state)
    Svc->>P: POST /token (exchange code)
    P-->>Svc: id_token, access_token
    Svc->>P: GET /userinfo
    P-->>Svc: email, sub
    Svc->>OA: get_by_provider_subject(provider, sub)
    alt linked
        Svc->>UR: get(linked.user_id)
    else first time
        Svc->>UR: get_or_create_by_email(email)
        Svc->>OA: insert(provider, sub, encrypted_tokens, user_id)
    end
    Svc->>RT: insert refresh token row
    Svc->>Svc: sign access JWT
    Svc-->>API: TokenPair
    API-->>Browser: 200 / set-cookie / redirect (per client)
```

## API-key authentication (per request)

API keys exist for headless clients (SDK, scripts). They short-circuit
JWT verification.

```mermaid
sequenceDiagram
    autonumber
    actor C as Client
    participant API as FastAPI middleware
    participant Dep as api/deps.get_current_user
    participant AKS as ApiKeyService
    participant AKR as ApiKeyRepository

    C->>API: any request<br/>Authorization: Bearer sb_live_… (prefix detected)
    API->>Dep: resolve current_user
    Dep->>AKS: authenticate(raw_key)
    AKS->>AKS: split prefix; sha256 the rest
    AKS->>AKR: get_by_key_hash(hash)
    alt missing / revoked / expired
        AKS-->>Dep: AuthError
        Dep-->>C: 401 Problem Details
    else valid
        AKS->>AKR: touch(last_used_at=now)
        AKS-->>Dep: AuthenticatedUser(role, scopes from key)
    end
    Dep-->>API: AuthenticatedUser
```

## RBAC enforcement (`require_role`)

```mermaid
flowchart TD
    REQ[Incoming request]
    DEP[api/deps.require_role role,...]
    AUTH[get_current_user]
    CHK{user.role ∈ allowed?}
    OK[hand control to router]
    DENY[403 forbidden Problem Details]

    REQ --> DEP --> AUTH --> CHK
    CHK -- yes --> OK
    CHK -- no  --> DENY
```

## Roles and what they can do

| Role | Reads | Writes |
|---|---|---|
| `end_user` | own batches only | submit `POST /analyze`, manage own profile + own API keys |
| `ai_developer` | any batch (read), any model, experiments | register / promote models, run experiments, **per-request `model_id` override on `/analyze`** |
| `admin` | everything | everything (including user role changes, supplier creation) |

The `model_id` override is the single most-tested authz boundary — see
`tests/unit/test_analysis_service.py::TestModelIdOverrideAuthz`.
