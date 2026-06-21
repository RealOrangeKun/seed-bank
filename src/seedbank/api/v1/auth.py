"""Auth router — register / login / refresh / logout / verify / OAuth.

Routers parse → call service → return DTO. They never touch SQLAlchemy and
never raise ``HTTPException`` for domain reasons (services raise
``core.exceptions.*``, the global error handler maps them).

Auth endpoints are documented exceptions to RESTful URL design — login,
refresh, logout, verify-email, and OAuth callbacks are not CRUD on a
resource; they're protocol steps. They stay under ``/auth/...``. Every other
endpoint should pick the resource shape (see the ``add-endpoint`` skill).
"""

from __future__ import annotations

from fastapi import APIRouter, Request, status

from seedbank.api.deps import AuthServiceDep, SettingsDep
from seedbank.api.rate_limit import limiter
from seedbank.core.config import get_settings
from seedbank.core.exceptions import AuthError, ExternalServiceError
from seedbank.infrastructure.oauth import get_oauth, github, google
from seedbank.schemas.auth import (
    BootstrapAdminIn,
    LoginIn,
    LogoutIn,
    MeOut,
    MessageOut,
    RefreshIn,
    RegisterIn,
    TokenPair,
    VerifyEmailIn,
)
from seedbank.schemas.common import Envelope
from seedbank.services.auth_service import TokenPair as ServiceTokenPair

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_token_pair_dto(pair: ServiceTokenPair) -> TokenPair:
    return TokenPair(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
    )


def _client_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host


_LIMIT_REGISTER = f"{get_settings().rate_limit_register_per_minute}/minute"
_LIMIT_LOGIN = f"{get_settings().rate_limit_login_per_minute}/minute"
_LIMIT_REFRESH = f"{get_settings().rate_limit_refresh_per_minute}/minute"


@router.post(
    "/bootstrap-admin",
    response_model=Envelope[MeOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create the first admin user",
    description=(
        "One-shot endpoint for installing the first admin in a fresh "
        "deployment. Idempotent: returns 409 once any admin exists. "
        "Disabled unless ``SEEDBANK_BOOTSTRAP_TOKEN`` is configured; the "
        "request must present the matching token."
    ),
)
@limiter.limit(_LIMIT_REGISTER)
async def bootstrap_admin(
    request: Request,
    payload: BootstrapAdminIn,
    service: AuthServiceDep,
) -> Envelope[MeOut]:
    user = await service.bootstrap_admin(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        bootstrap_token=payload.bootstrap_token,
        ip=_client_ip(request),
    )
    return Envelope[MeOut](data=MeOut.model_validate(user))


@router.post(
    "/register",
    response_model=Envelope[MessageOut],
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(_LIMIT_REGISTER)
async def register(
    request: Request,
    payload: RegisterIn,
    service: AuthServiceDep,
) -> Envelope[MessageOut]:
    await service.register(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        ip=_client_ip(request),
    )
    return Envelope[MessageOut](
        data=MessageOut(message="Registered. Check your email for a verification link.")
    )


@router.post("/verify-email", response_model=Envelope[MessageOut])
async def verify_email(payload: VerifyEmailIn, service: AuthServiceDep) -> Envelope[MessageOut]:
    await service.verify_email(token=payload.token)
    return Envelope[MessageOut](data=MessageOut(message="Email verified."))


@router.post("/login", response_model=Envelope[TokenPair])
@limiter.limit(_LIMIT_LOGIN)
async def login(
    request: Request,
    payload: LoginIn,
    service: AuthServiceDep,
) -> Envelope[TokenPair]:
    _user, pair = await service.login(
        email=payload.email,
        password=payload.password,
        ip=_client_ip(request),
    )
    return Envelope[TokenPair](data=_to_token_pair_dto(pair))


@router.post("/refresh", response_model=Envelope[TokenPair])
@limiter.limit(_LIMIT_REFRESH)
async def refresh(
    request: Request,
    payload: RefreshIn,
    service: AuthServiceDep,
) -> Envelope[TokenPair]:
    _user, pair = await service.refresh(
        refresh_token=payload.refresh_token,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return Envelope[TokenPair](data=_to_token_pair_dto(pair))


@router.post("/logout", response_model=Envelope[MessageOut])
async def logout(payload: LogoutIn, service: AuthServiceDep) -> Envelope[MessageOut]:
    await service.logout(refresh_token=payload.refresh_token)
    return Envelope[MessageOut](data=MessageOut(message="Logged out."))


# ── OAuth ───────────────────────────────────────────────────────────────────


def _provider_module(provider: str):
    if provider == google.PROVIDER_NAME:
        return google
    if provider == github.PROVIDER_NAME:
        return github
    return None


@router.get("/oauth/{provider}/login")
async def oauth_login(
    provider: str,
    request: Request,
    settings: SettingsDep,
):
    mod = _provider_module(provider)
    if mod is None:
        raise AuthError(f"Unknown OAuth provider: {provider}")
    if not mod.is_configured(settings):
        raise ExternalServiceError(f"{provider} OAuth is not configured.")
    redirect_uri = (
        f"{settings.oauth_redirect_base_url}{settings.api_v1_prefix}/auth/oauth/{provider}/callback"
    )
    return await mod.authorize_redirect(get_oauth(settings), request, redirect_uri)


@router.get("/oauth/{provider}/callback", response_model=Envelope[TokenPair])
async def oauth_callback(
    provider: str,
    request: Request,
    service: AuthServiceDep,
    settings: SettingsDep,
) -> Envelope[TokenPair]:
    mod = _provider_module(provider)
    if mod is None:
        raise AuthError(f"Unknown OAuth provider: {provider}")
    if not mod.is_configured(settings):
        raise ExternalServiceError(f"{provider} OAuth is not configured.")

    identity = await mod.fetch_identity(get_oauth(settings), request)
    _user, pair = await service.upsert_oauth_user(
        identity=identity,
        ip=_client_ip(request),
    )
    return Envelope[TokenPair](data=_to_token_pair_dto(pair))


__all__ = ["router"]
