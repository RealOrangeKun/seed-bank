"""GitHub OAuth2 client (authlib).

Same shape as the Google client. GitHub doesn't always return the user's
email in `/user`, so we fall through to `/user/emails` when needed.
"""

from __future__ import annotations

from typing import Any

from authlib.integrations.starlette_client import OAuth, OAuthError
from starlette.requests import Request

from seedbank.core.config import Settings
from seedbank.core.exceptions import AuthError, ExternalServiceError
from seedbank.domain.user import OAuthIdentity

PROVIDER_NAME = "github"


def register(oauth: OAuth, settings: Settings) -> None:
    if settings.oauth_github_client_id is None or settings.oauth_github_client_secret is None:
        return
    oauth.register(
        name=PROVIDER_NAME,
        client_id=settings.oauth_github_client_id.get_secret_value(),
        client_secret=settings.oauth_github_client_secret.get_secret_value(),
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "read:user user:email"},
    )


def is_configured(settings: Settings) -> bool:
    return (
        settings.oauth_github_client_id is not None
        and settings.oauth_github_client_secret is not None
    )


async def authorize_redirect(oauth: OAuth, request: Request, redirect_uri: str) -> Any:
    client = oauth.create_client(PROVIDER_NAME)
    if client is None:
        raise ExternalServiceError("GitHub OAuth is not configured.")
    return await client.authorize_redirect(request, redirect_uri)


async def fetch_identity(oauth: OAuth, request: Request) -> OAuthIdentity:
    client = oauth.create_client(PROVIDER_NAME)
    if client is None:
        raise ExternalServiceError("GitHub OAuth is not configured.")
    try:
        token = await client.authorize_access_token(request)
        profile_resp = await client.get("user", token=token)
    except OAuthError as exc:
        raise AuthError("GitHub authentication failed.") from exc

    profile: dict[str, Any] = profile_resp.json()
    sub = profile.get("id")
    if sub is None:
        raise AuthError("GitHub profile did not include an id.")

    email = profile.get("email")
    if not email:
        emails_resp = await client.get("user/emails", token=token)
        emails: list[dict[str, Any]] = emails_resp.json() or []
        primary = next((e for e in emails if e.get("primary") and e.get("verified")), None)
        if primary is None:
            primary = next((e for e in emails if e.get("verified")), None)
        if primary is None:
            raise AuthError("No verified email associated with the GitHub account.")
        email = primary.get("email")

    if not email:
        raise AuthError("GitHub profile did not include an email.")

    return OAuthIdentity(
        provider=PROVIDER_NAME,
        subject=str(sub),
        email=str(email),
        full_name=profile.get("name") or profile.get("login"),
    )


__all__ = [
    "PROVIDER_NAME",
    "authorize_redirect",
    "fetch_identity",
    "is_configured",
    "register",
]
