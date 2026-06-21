"""FastAPI dependencies — the only place routers reach into infrastructure.

Routers depend on these getters; they never instantiate engines, clients, or
services themselves. The `current_user` / `require_role` / `require_scope`
dependencies live here too so RBAC is one decoration away on any route.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import Depends, Header, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from seedbank.core.config import Settings, get_settings
from seedbank.core.exceptions import AuthError, ForbiddenError
from seedbank.core.security import (
    JWT_TYPE_ACCESS,
    decode_jwt,
    looks_like_api_key,
    sha256_hex,
)
from seedbank.domain.user import AuthenticatedUser, Role
from seedbank.infrastructure.analytics import ClickHouseClient, get_clickhouse
from seedbank.infrastructure.cache import get_redis
from seedbank.infrastructure.db.repositories import (
    ApiKeyRepository,
    DatasetItemRepository,
    DatasetRepository,
    ExperimentRepository,
    ExperimentResultRepository,
    ModelArtifactRepository,
    ModelMetricRepository,
    OAuthAccountRepository,
    RefreshTokenRepository,
    ScanBatchRepository,
    ScanImageRepository,
    UserRepository,
)
from seedbank.infrastructure.db.session import get_db as _get_db
from seedbank.infrastructure.storage import MinioStorage, get_storage
from seedbank.services.analysis_service import AnalysisService
from seedbank.services.api_key_service import ApiKeyService
from seedbank.services.auth_service import AuthService
from seedbank.services.batch_service import BatchService
from seedbank.services.dataset_service import DatasetService
from seedbank.services.experiment_service import ExperimentService

log = structlog.get_logger(__name__)


async def db_session() -> AsyncIterator[AsyncSession]:
    """Yield an `AsyncSession` for the lifetime of one request."""
    async for s in _get_db():
        yield s


def settings_dep() -> Settings:
    return get_settings()


def redis_dep() -> Redis:
    return get_redis()


def storage_dep() -> MinioStorage:
    return get_storage()


async def clickhouse_dep() -> ClickHouseClient:
    return await get_clickhouse()


# Type aliases for terser router signatures.
DbSession = Annotated[AsyncSession, Depends(db_session)]
SettingsDep = Annotated[Settings, Depends(settings_dep)]
RedisDep = Annotated[Redis, Depends(redis_dep)]
StorageDep = Annotated[MinioStorage, Depends(storage_dep)]
ClickHouseDep = Annotated[ClickHouseClient, Depends(clickhouse_dep)]


# ── Repository factories ─────────────────────────────────────────────────────


def user_repo(session: DbSession) -> UserRepository:
    return UserRepository(session)


def refresh_token_repo(session: DbSession) -> RefreshTokenRepository:
    return RefreshTokenRepository(session)


def oauth_account_repo(session: DbSession) -> OAuthAccountRepository:
    return OAuthAccountRepository(session)


def api_key_repo(session: DbSession) -> ApiKeyRepository:
    return ApiKeyRepository(session)


def scan_batch_repo(session: DbSession) -> ScanBatchRepository:
    return ScanBatchRepository(session)


def scan_image_repo(session: DbSession) -> ScanImageRepository:
    return ScanImageRepository(session)


def dataset_repo(session: DbSession) -> DatasetRepository:
    return DatasetRepository(session)


def dataset_item_repo(session: DbSession) -> DatasetItemRepository:
    return DatasetItemRepository(session)


def experiment_repo(session: DbSession) -> ExperimentRepository:
    return ExperimentRepository(session)


def experiment_result_repo(session: DbSession) -> ExperimentResultRepository:
    return ExperimentResultRepository(session)


def model_artifact_repo(session: DbSession) -> ModelArtifactRepository:
    return ModelArtifactRepository(session)


def model_metric_repo(session: DbSession) -> ModelMetricRepository:
    return ModelMetricRepository(session)


UserRepoDep = Annotated[UserRepository, Depends(user_repo)]
RefreshTokenRepoDep = Annotated[RefreshTokenRepository, Depends(refresh_token_repo)]
OAuthAccountRepoDep = Annotated[OAuthAccountRepository, Depends(oauth_account_repo)]
ApiKeyRepoDep = Annotated[ApiKeyRepository, Depends(api_key_repo)]
ScanBatchRepoDep = Annotated[ScanBatchRepository, Depends(scan_batch_repo)]
ScanImageRepoDep = Annotated[ScanImageRepository, Depends(scan_image_repo)]
DatasetRepoDep = Annotated[DatasetRepository, Depends(dataset_repo)]
DatasetItemRepoDep = Annotated[DatasetItemRepository, Depends(dataset_item_repo)]
ExperimentRepoDep = Annotated[ExperimentRepository, Depends(experiment_repo)]
ExperimentResultRepoDep = Annotated[ExperimentResultRepository, Depends(experiment_result_repo)]
ModelArtifactRepoDep = Annotated[ModelArtifactRepository, Depends(model_artifact_repo)]
ModelMetricRepoDep = Annotated[ModelMetricRepository, Depends(model_metric_repo)]


# ── Service factories ────────────────────────────────────────────────────────


def auth_service(
    session: DbSession,
    users: UserRepoDep,
    refresh_tokens: RefreshTokenRepoDep,
    oauth_accounts: OAuthAccountRepoDep,
    redis: RedisDep,
    settings: SettingsDep,
) -> AuthService:
    return AuthService(
        session=session,
        users=users,
        refresh_tokens=refresh_tokens,
        oauth_accounts=oauth_accounts,
        redis=redis,
        settings=settings,
    )


def api_key_service(
    session: DbSession,
    api_keys: ApiKeyRepoDep,
    settings: SettingsDep,
) -> ApiKeyService:
    return ApiKeyService(session=session, api_keys=api_keys, settings=settings)


def analysis_service(
    session: DbSession,
    batches: ScanBatchRepoDep,
    images: ScanImageRepoDep,
    settings: SettingsDep,
    storage: StorageDep,
) -> AnalysisService:
    return AnalysisService(
        session=session,
        batches=batches,
        images=images,
        settings=settings,
        storage=storage,
    )


def batch_service(
    session: DbSession,
    batches: ScanBatchRepoDep,
    images: ScanImageRepoDep,
    storage: StorageDep,
    settings: SettingsDep,
) -> BatchService:
    return BatchService(
        session=session,
        batches=batches,
        images=images,
        storage=storage,
        settings=settings,
    )


def dataset_service(
    session: DbSession,
    datasets: DatasetRepoDep,
    items: DatasetItemRepoDep,
) -> DatasetService:
    return DatasetService(session=session, datasets=datasets, items=items)


def experiment_service(
    session: DbSession,
    experiments: ExperimentRepoDep,
    results: ExperimentResultRepoDep,
    models: ModelArtifactRepoDep,
    datasets: DatasetRepoDep,
) -> ExperimentService:
    return ExperimentService(
        session=session,
        experiments=experiments,
        results=results,
        models=models,
        datasets=datasets,
    )


AuthServiceDep = Annotated[AuthService, Depends(auth_service)]
ApiKeyServiceDep = Annotated[ApiKeyService, Depends(api_key_service)]
AnalysisServiceDep = Annotated[AnalysisService, Depends(analysis_service)]
BatchServiceDep = Annotated[BatchService, Depends(batch_service)]
DatasetServiceDep = Annotated[DatasetService, Depends(dataset_service)]
ExperimentServiceDep = Annotated[ExperimentService, Depends(experiment_service)]


# ── Authentication ───────────────────────────────────────────────────────────


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


async def _resolve_via_jwt(
    token: str, users: UserRepository, settings: Settings
) -> AuthenticatedUser:
    payload = decode_jwt(token, expected_type=JWT_TYPE_ACCESS, settings=settings)
    sub = payload.get("sub")
    if not isinstance(sub, str):
        raise AuthError("Invalid token subject.")
    try:
        user_id = UUID(sub)
    except ValueError as exc:
        raise AuthError("Invalid token subject.") from exc
    user = await users.get_by_id_active(user_id)
    if user is None:
        raise AuthError("User no longer active.")
    return AuthenticatedUser(
        id=user.id,
        email=user.email,
        role=Role(user.role),
        is_active=user.is_active,
        is_verified=user.is_verified,
        scopes=frozenset(),
        auth_method="jwt",
    )


async def _resolve_via_api_key(
    raw_key: str,
    api_keys: ApiKeyRepository,
    users: UserRepository,
    settings: Settings,
) -> AuthenticatedUser:
    if not looks_like_api_key(raw_key, settings):
        raise AuthError("Invalid API key.")
    record = await api_keys.get_active_by_hash(sha256_hex(raw_key))
    if record is None:
        raise AuthError("Invalid API key.")
    user = await users.get_by_id_active(record.user_id)
    if user is None:
        raise AuthError("API key owner is inactive.")
    await api_keys.touch_last_used(record.id)
    return AuthenticatedUser(
        id=user.id,
        email=user.email,
        role=Role(user.role),
        is_active=user.is_active,
        is_verified=user.is_verified,
        scopes=frozenset(record.scopes or ()),
        auth_method="api_key",
    )


async def current_user(
    request: Request,
    users: UserRepoDep,
    api_keys: ApiKeyRepoDep,
    settings: SettingsDep,
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> AuthenticatedUser:
    """Resolve the calling actor from `Authorization: Bearer ...` or
    `X-API-Key`. Raises `AuthError` (→ 401) on any failure.

    JWT takes precedence if both headers are sent; we never silently fall
    back from a malformed JWT to an API key — that's a phishing vector.
    """
    bearer = _bearer_token(authorization)
    if bearer is not None:
        actor = await _resolve_via_jwt(bearer, users, settings)
    elif x_api_key:
        actor = await _resolve_via_api_key(x_api_key, api_keys, users, settings)
    else:
        raise AuthError("Authentication required.")

    structlog.contextvars.bind_contextvars(user_id=str(actor.id), auth_method=actor.auth_method)
    request.state.user = actor
    return actor


CurrentUser = Annotated[AuthenticatedUser, Depends(current_user)]


def require_role(*roles: Role) -> Callable[..., Awaitable[AuthenticatedUser]]:
    """Dependency factory: require the actor's role to be one of `roles`.

    Admins implicitly satisfy any role check (see `AuthenticatedUser.has_role`).
    """
    role_set = frozenset(roles)

    # Pre-compute the message: "admin"-only routes already say it; everything
    # else mentions that admin satisfies the check too, since admins
    # implicitly pass any `require_role(...)` gate.
    non_admin = sorted(r.value for r in role_set if r is not Role.ADMIN)
    if not non_admin:
        _msg = "Requires admin."
    else:
        _msg = f"Requires admin or one of roles: {', '.join(non_admin)}."

    async def _checker(actor: CurrentUser) -> AuthenticatedUser:
        if actor.is_admin or actor.role in role_set:
            return actor
        raise ForbiddenError(_msg)

    return _checker


def require_scope(*scopes: str) -> Callable[..., Awaitable[AuthenticatedUser]]:
    """Dependency factory: require all `scopes` on an API-key actor (JWT
    actors are gated by `require_role`)."""
    required = frozenset(scopes)

    async def _checker(actor: CurrentUser) -> AuthenticatedUser:
        if actor.auth_method == "jwt":
            return actor
        missing = required - actor.scopes
        if missing:
            raise ForbiddenError(f"API key is missing scopes: {', '.join(sorted(missing))}.")
        return actor

    return _checker
