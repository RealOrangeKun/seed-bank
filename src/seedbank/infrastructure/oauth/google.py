"""Google OAuth2 client (authlib).

Thin adapter around `authlib.integrations.starlette_client`. Exposes:

- `register(oauth)`: registers the `"google"` provider on a shared
  `OAuth` instance.
- `authorize_redirect(request, ...)`: produces the redirect-to-Google response.
- `fetch_identity(request)`: exchanges the auth code for an ID token and
  returns a normalized `OAuthIdentity`.

We never persist Google's access/refresh tokens at this stage — the only
information we need from Google is the immutable `sub` and email, used for
account linking in `auth_service.upsert_oauth_user`.
"""

from __future__ import annotations

from typing import Any

from authlib.integrations.starlette_client import OAuth, OAuthError
from starlette.requests import Request

from seedbank.core.config import Settings
from seedbank.core.exceptions import AuthError, ExternalServiceError
from seedbank.domain.user import OAuthIdentity

PROVIDER_NAME = "google"
_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"


def register(oauth: OAuth, settings: Settings) -> None:
    if settings.oauth_google_client_id is None or settings.oauth_google_client_secret is None:
        return
    oauth.register(
        name=PROVIDER_NAME,
        client_id=settings.oauth_google_client_id.get_secret_value(),
        client_secret=settings.oauth_google_client_secret.get_secret_value(),
        server_metadata_url=_DISCOVERY_URL,
        client_kwargs={"scope": "openid email profile"},
    )


def is_configured(settings: Settings) -> bool:
    return (
        settings.oauth_google_client_id is not None
        and settings.oauth_google_client_secret is not None
    )


async def authorize_redirect(oauth: OAuth, request: Request, redirect_uri: str) -> Any:
    client = oauth.create_client(PROVIDER_NAME)
    if client is None:
        raise ExternalServiceError("Google OAuth is not configured.")
    return await client.authorize_redirect(request, redirect_uri)


async def fetch_identity(oauth: OAuth, request: Request) -> OAuthIdentity:
    client = oauth.create_client(PROVIDER_NAME)
    if client is None:
        raise ExternalServiceError("Google OAuth is not configured.")
    try:
        token = await client.authorize_access_token(request)
    except OAuthError as exc:
        raise AuthError("Google authentication failed.") from exc

    userinfo: dict[str, Any] | None = token.get("userinfo")
    if not userinfo:
        # Fall back to the userinfo endpoint when the ID token didn't carry it.
        try:
            resp = await client.userinfo(token=token)
        except OAuthError as exc:
            raise AuthError("Failed to read Google profile.") from exc
        userinfo = dict(resp)

    sub = userinfo.get("sub")
    email = userinfo.get("email")
    if not sub or not email:
        raise AuthError("Google profile did not include sub/email.")

    return OAuthIdentity(
        provider=PROVIDER_NAME,
        subject=str(sub),
        email=str(email),
        full_name=userinfo.get("name"),
    )


__all__ = [
    "PROVIDER_NAME",
    "authorize_redirect",
    "fetch_identity",
    "is_configured",
    "register",
]
