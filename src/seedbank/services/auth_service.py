"""Auth service — orchestrates registration, login, token refresh, and OAuth.

Hard rules enforced here:

- **`password OR oauth` invariant**: a freshly-created user must have either a
  password hash or at least one linked OAuth account before commit. The DB
  schema can't express this cross-table check, so it lives here.
- **No FastAPI imports**: this module raises `core.exceptions.*` errors only.
- **Refresh-token rotation**: `refresh()` revokes the presented token and
  issues a new pair atomically. A second use of an already-rotated token
  returns AuthError (replay detection via `RefreshTokenRepository.rotate`
  rowcount = 0).
- **Audit log**: register, login (success + failure), password change, oauth
  link, role change all write one `audit_log` row each.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from seedbank.core.config import Settings
from seedbank.core.exceptions import (
    AuthError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from seedbank.core.logging import get_logger
from seedbank.core.metrics import AUTH_LOGIN
from seedbank.core.security import (
    JWT_TYPE_REFRESH,
    decode_jwt,
    enforce_password_policy,
    generate_verification_token,
    hash_password,
    issue_access_token,
    issue_refresh_token,
    sha256_hex,
    verify_password,
)
from seedbank.domain.user import OAuthIdentity, Role
from seedbank.infrastructure.db.models import (
    AuditLog,
    OAuthAccount,
    RefreshToken,
    User,
)
from seedbank.infrastructure.db.repositories import (
    OAuthAccountRepository,
    RefreshTokenRepository,
    UserRepository,
)

log = get_logger(__name__)

_VERIFY_REDIS_PREFIX = "auth:verify:"


@dataclass(frozen=True, slots=True)
class TokenPair:
    """Plain transport object — converted to the Pydantic schema at the API edge."""

    access_token: str
    refresh_token: str
    expires_in: int


class AuthService:
    """The single use-case orchestrator for authentication.

    A new instance is built per request (FastAPI dependency wiring) so the
    underlying `AsyncSession` is request-scoped.
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        oauth_accounts: OAuthAccountRepository,
        redis: Redis,
        settings: Settings,
    ) -> None:
        self.session = session
        self.users = users
        self.refresh_tokens = refresh_tokens
        self.oauth_accounts = oauth_accounts
        self.redis = redis
        self.settings = settings

    # ── First-admin bootstrap ────────────────────────────────────────────────

    async def bootstrap_admin(
        self,
        *,
        email: str,
        password: str,
        full_name: str | None,
        bootstrap_token: str,
        ip: str | None = None,
    ) -> User:
        """Create the very first admin user.

        Idempotent in spirit: rejects with ``ConflictError`` once any
        admin exists, so calling it twice can never produce two admins.
        Gated by ``Settings.bootstrap_token`` — the endpoint is disabled
        unless the operator has set the env var, and the request must
        present the matching value. A constant-time comparison avoids
        leaking the token through timing side-channels.

        Returns the persisted ``User`` row (already verified + active so
        the operator can immediately log in via ``/auth/login``).
        """
        import hmac

        configured = (
            self.settings.bootstrap_token.get_secret_value()
            if self.settings.bootstrap_token is not None
            else None
        )
        if not configured or not hmac.compare_digest(configured, bootstrap_token):
            log.warning("auth.bootstrap_admin_rejected", reason="invalid_token", ip=ip)
            raise AuthError("Invalid bootstrap token.")

        if await self.users.exists_with_role(Role.ADMIN.value):
            raise ConflictError("An admin user already exists.")

        enforce_password_policy(password)

        # Email-uniqueness still applies — guard explicitly so the caller
        # gets a 409 instead of a generic IntegrityError.
        if await self.users.get_by_email(email) is not None:
            raise ConflictError("Email already registered.")

        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=Role.ADMIN.value,
            is_active=True,
            is_verified=True,
        )
        await self.users.add(user)

        await self._audit(
            actor_id=user.id,
            action="user.bootstrap_admin",
            target=user,
            ip=ip,
            metadata={"email": email},
        )

        await self.session.commit()
        log.info("auth.bootstrap_admin_created", user_id=str(user.id), email=email)
        return user

    # ── Registration ─────────────────────────────────────────────────────────

    async def register(
        self,
        *,
        email: str,
        password: str,
        full_name: str | None,
        ip: str | None = None,
    ) -> tuple[User, str]:
        """Create a new password user. Returns `(user, verification_token)`.

        The verification token is intentionally returned (not emailed) — the
        notification path is a Phase-4 follow-up. We log a structured event
        with the link so dev environments can complete the flow manually.
        """
        enforce_password_policy(password)

        existing = await self.users.get_by_email(email)
        if existing is not None:
            raise ConflictError("Email already registered.")

        hashed = hash_password(password)
        user = User(
            email=email,
            hashed_password=hashed,
            full_name=full_name,
            role=Role.END_USER.value,
            is_active=True,
            is_verified=False,
        )
        await self.users.add(user)

        plaintext_token, token_hash = generate_verification_token()
        await self.redis.set(
            f"{_VERIFY_REDIS_PREFIX}{token_hash}",
            str(user.id),
            ex=self.settings.email_verification_ttl_seconds,
        )

        await self._audit(
            actor_id=user.id,
            action="user.register",
            target=user,
            ip=ip,
            metadata={"email": email},
        )

        # TODO(phase-4-followup): hand off to a notification worker.
        log.info(
            "auth.verification_token_issued",
            user_id=str(user.id),
            verify_link=f"{self.settings.oauth_redirect_base_url}"
            f"{self.settings.api_v1_prefix}/auth/verify-email"
            f"?token={plaintext_token}",
        )

        await self.session.commit()
        return user, plaintext_token

    async def verify_email(self, *, token: str) -> User:
        token_hash = sha256_hex(token)
        key = f"{_VERIFY_REDIS_PREFIX}{token_hash}"
        user_id_str = await self.redis.get(key)
        if user_id_str is None:
            raise AuthError("Invalid or expired verification token.")
        user_id = UUID(str(user_id_str))
        await self.redis.delete(key)

        rowcount = await self.users.mark_verified(user_id)
        if rowcount == 0:
            # User missing or already verified — treat both as success-ish.
            user = await self.users.get(user_id)
            if user is None:
                raise NotFoundError("User no longer exists.")
        else:
            user = await self.users.get(user_id)
            assert user is not None

        await self.session.commit()
        return user

    # ── Login + token issuance ───────────────────────────────────────────────

    async def login(
        self, *, email: str, password: str, ip: str | None = None
    ) -> tuple[User, TokenPair]:
        user = await self.users.get_by_email(email)
        if user is None or user.hashed_password is None:
            await self._audit(
                actor_id=None,
                action="user.login_failed",
                metadata={"email": email, "reason": "no_user"},
                ip=ip,
            )
            await self.session.commit()
            AUTH_LOGIN.labels(result="invalid_credentials").inc()
            raise AuthError("Invalid email or password.")

        if not verify_password(password, user.hashed_password):
            await self._audit(
                actor_id=user.id,
                action="user.login_failed",
                metadata={"email": email, "reason": "bad_password"},
                ip=ip,
            )
            await self.session.commit()
            AUTH_LOGIN.labels(result="invalid_credentials").inc()
            raise AuthError("Invalid email or password.")

        if not user.is_active:
            AUTH_LOGIN.labels(result="blocked").inc()
            raise ForbiddenError("Account is disabled.")
        if not user.is_verified:
            AUTH_LOGIN.labels(result="blocked").inc()
            raise ForbiddenError("Email not verified.")

        pair = await self._issue_token_pair(user, ip=ip, user_agent=None)
        await self.users.touch_last_login(user.id)
        await self._audit(
            actor_id=user.id,
            action="user.login",
            target=user,
            ip=ip,
        )
        await self.session.commit()
        AUTH_LOGIN.labels(result="ok").inc()
        return user, pair

    async def refresh(
        self,
        *,
        refresh_token: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, TokenPair]:
        # Validate signature and expiry first; cheap and avoids a DB hit on
        # garbage tokens.
        payload = decode_jwt(refresh_token, expected_type=JWT_TYPE_REFRESH)
        sub = payload.get("sub")
        if not isinstance(sub, str):
            raise AuthError("Invalid token.")

        token_hash = sha256_hex(refresh_token)
        existing = await self.refresh_tokens.get_active_by_hash(token_hash)
        if existing is None:
            # Either never existed, expired, or was revoked — likely a replay
            # of an already-rotated token. Defensive measure: revoke the whole
            # family for that user.
            try:
                user_id = UUID(sub)
                await self.refresh_tokens.revoke_all_for_user(user_id)
                await self.session.commit()
            except ValueError:
                pass
            raise AuthError("Refresh token is no longer valid.")

        user = await self.users.get_by_id_active(existing.user_id)
        if user is None:
            raise AuthError("User no longer active.")

        pair, new_token_id = await self._issue_token_pair_returning_id(
            user,
            ip=ip,
            user_agent=user_agent,
        )
        rowcount = await self.refresh_tokens.rotate(existing.id, new_token_id)
        if rowcount == 0:
            # Lost the race to another rotation — treat as replay.
            raise AuthError("Refresh token is no longer valid.")

        await self.session.commit()
        return user, pair

    async def logout(self, *, refresh_token: str) -> None:
        """Revoke the supplied refresh token. Idempotent."""
        token_hash = sha256_hex(refresh_token)
        existing = await self.refresh_tokens.get_active_by_hash(token_hash)
        if existing is None:
            await self.session.commit()
            return
        existing.revoked_at = datetime.now(tz=UTC)
        await self.session.commit()

    # ── Password change ──────────────────────────────────────────────────────

    async def change_password(
        self,
        *,
        user_id: UUID,
        current_password: str,
        new_password: str,
        ip: str | None = None,
    ) -> None:
        user = await self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found.")
        if user.hashed_password is None or not verify_password(
            current_password, user.hashed_password
        ):
            raise AuthError("Current password is incorrect.")
        enforce_password_policy(new_password)

        await self.users.update_password(user_id, hash_password(new_password))
        # Force-logout: revoke every active refresh token after a password
        # change. Belt-and-braces against credential stuffing.
        await self.refresh_tokens.revoke_all_for_user(user_id)
        await self._audit(
            actor_id=user_id,
            action="user.password_change",
            target=user,
            ip=ip,
        )
        await self.session.commit()

    # ── OAuth ────────────────────────────────────────────────────────────────

    async def upsert_oauth_user(
        self, *, identity: OAuthIdentity, ip: str | None = None
    ) -> tuple[User, TokenPair]:
        """Create-or-link the OAuth identity, then issue a fresh token pair."""
        existing_link = await self.oauth_accounts.get_by_provider_subject(
            identity.provider,
            identity.subject,
        )
        if existing_link is not None:
            user = await self.users.get(existing_link.user_id)
            if user is None or not user.is_active:
                AUTH_LOGIN.labels(result="blocked").inc()
                raise ForbiddenError("Account is disabled.")
        else:
            user = await self.users.get_by_email(identity.email)
            if user is None:
                user = User(
                    email=identity.email,
                    hashed_password=None,
                    full_name=identity.full_name,
                    role=Role.END_USER.value,
                    is_active=True,
                    # OAuth providers have already verified the email.
                    is_verified=True,
                )
                await self.users.add(user)
            self.session.add(
                OAuthAccount(
                    user_id=user.id,
                    provider=identity.provider,
                    provider_subject=identity.subject,
                )
            )
            await self.session.flush()
            await self._audit(
                actor_id=user.id,
                action="user.oauth_link",
                metadata={"provider": identity.provider},
                ip=ip,
            )

        # Cross-table invariant: a user must have password OR oauth.
        await self._assert_password_or_oauth(user)

        pair = await self._issue_token_pair(user, ip=ip, user_agent=None)
        await self.users.touch_last_login(user.id)
        await self._audit(
            actor_id=user.id,
            action="user.login",
            metadata={"provider": identity.provider},
            ip=ip,
        )
        await self.session.commit()
        # OAuth success collapses onto the same ``ok`` label as password
        # login — keeping the labelset to {ok, invalid_credentials, blocked}
        # avoids cardinality creep; the provider lives in audit_log instead.
        AUTH_LOGIN.labels(result="ok").inc()
        return user, pair

    # ── Role management (admin) ──────────────────────────────────────────────

    async def set_user_role(
        self,
        *,
        actor_id: UUID,
        target_user_id: UUID,
        role: Role,
        ip: str | None = None,
    ) -> User:
        rowcount = await self.users.set_role(target_user_id, role.value)
        if rowcount == 0:
            raise NotFoundError("Target user not found.")
        target = await self.users.get(target_user_id)
        assert target is not None
        await self._audit(
            actor_id=actor_id,
            action="user.role_change",
            target=target,
            metadata={"new_role": role.value},
            ip=ip,
        )
        await self.session.commit()
        return target

    # ── Internals ────────────────────────────────────────────────────────────

    async def _issue_token_pair(
        self,
        user: User,
        *,
        ip: str | None,
        user_agent: str | None,
    ) -> TokenPair:
        pair, _ = await self._issue_token_pair_returning_id(
            user,
            ip=ip,
            user_agent=user_agent,
        )
        return pair

    async def _issue_token_pair_returning_id(
        self,
        user: User,
        *,
        ip: str | None,
        user_agent: str | None,
    ) -> tuple[TokenPair, UUID]:
        access = issue_access_token(
            subject=str(user.id),
            role=user.role,
            settings=self.settings,
        )
        refresh, expires_at = issue_refresh_token(
            subject=str(user.id),
            settings=self.settings,
        )
        token_hash = sha256_hex(refresh)
        rt = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip=ip,
        )
        await self.refresh_tokens.add(rt)
        pair = TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=self.settings.jwt_access_ttl_seconds,
        )
        return pair, rt.id

    async def _assert_password_or_oauth(self, user: User) -> None:
        if user.hashed_password is not None:
            return
        existing = await self.oauth_accounts.find_by(user_id=user.id)
        if existing is None:
            raise ValidationError("User must have either a password or a linked OAuth account.")

    async def _audit(
        self,
        *,
        actor_id: UUID | None,
        action: str,
        target: Any | None = None,
        metadata: dict[str, Any] | None = None,
        ip: str | None = None,
    ) -> None:
        target_type: str | None = None
        target_id: str | None = None
        if target is not None:
            target_type = target.__class__.__name__.lower()
            target_id = str(getattr(target, "id", None))
        self.session.add(
            AuditLog(
                actor_id=actor_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                audit_metadata=metadata,
                ip=ip,
            )
        )


__all__ = ["AuthService", "TokenPair"]
