"""Security primitives — password hashing, JWT, API-key generation.

Pure functions over crypto libraries. Holds no I/O state and no DB references,
so it's freely importable from services and tests.

- bcrypt via passlib for password hashes (rounds from `Settings.bcrypt_rounds`).
- python-jose for JWT signing / decoding (HS256, secret from `Settings`).
- secrets + hashlib for refresh-token / API-key generation; we never store
  the raw value — only its SHA-256 hash.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from jose import JWTError, jwt
from passlib.context import CryptContext

from seedbank.core.config import Settings, get_settings
from seedbank.core.exceptions import AuthError, ValidationError

# ── Password hashing ─────────────────────────────────────────────────────────

# Lazily-built passlib context — bcrypt rounds come from Settings, but the
# context is process-global once built.
_pwd_context: CryptContext | None = None


def _get_pwd_context(settings: Settings | None = None) -> CryptContext:
    global _pwd_context
    if _pwd_context is None:
        s = settings or get_settings()
        _pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=s.bcrypt_rounds,
        )
    return _pwd_context


def hash_password(password: str) -> str:
    """Return a bcrypt hash of `password`. Raises `ValidationError` if the
    password is below the policy length."""
    enforce_password_policy(password)
    return _get_pwd_context().hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Constant-time compare via passlib. Returns False on any mismatch
    (including malformed hashes)."""
    try:
        return _get_pwd_context().verify(password, hashed)
    except (ValueError, TypeError):
        return False


# ── Password policy ──────────────────────────────────────────────────────────

PASSWORD_MIN_LENGTH: Final[int] = 12
_PWD_RE_LOWER = re.compile(r"[a-z]")
_PWD_RE_UPPER = re.compile(r"[A-Z]")
_PWD_RE_DIGIT = re.compile(r"\d")


def enforce_password_policy(password: str) -> None:
    """Reject weak passwords. Raises `ValidationError` with a human-readable
    detail.

    Policy: ≥ 12 chars, mix of upper/lower/digit. Symbols not required (we don't
    want to push users to reuse passwords elsewhere)."""
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValidationError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters.")
    if not _PWD_RE_LOWER.search(password):
        raise ValidationError("Password must contain a lowercase letter.")
    if not _PWD_RE_UPPER.search(password):
        raise ValidationError("Password must contain an uppercase letter.")
    if not _PWD_RE_DIGIT.search(password):
        raise ValidationError("Password must contain a digit.")


# ── JWT helpers ──────────────────────────────────────────────────────────────

JWT_TYPE_ACCESS: Final[str] = "access"
JWT_TYPE_REFRESH: Final[str] = "refresh"


def _now_utc() -> datetime:
    return datetime.now(tz=UTC)


def encode_jwt(
    *,
    subject: str,
    token_type: str,
    expires_in_seconds: int,
    extra_claims: dict[str, Any] | None = None,
    settings: Settings | None = None,
) -> str:
    """Encode a JWT with `sub`, `type`, `iat`, `exp`, `jti` claims."""
    s = settings or get_settings()
    now = _now_utc()
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in_seconds)).timestamp()),
        "jti": secrets.token_urlsafe(16),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(
        payload,
        s.jwt_secret.get_secret_value(),
        algorithm=s.jwt_algorithm,
    )


def decode_jwt(
    token: str,
    *,
    expected_type: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Decode + validate a JWT. Raises `AuthError` on any failure."""
    s = settings or get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            s.jwt_secret.get_secret_value(),
            algorithms=[s.jwt_algorithm],
        )
    except JWTError as exc:
        raise AuthError("Invalid or expired token.") from exc
    if expected_type is not None and payload.get("type") != expected_type:
        raise AuthError("Token type mismatch.")
    return payload


def issue_access_token(*, subject: str, role: str, settings: Settings | None = None) -> str:
    s = settings or get_settings()
    return encode_jwt(
        subject=subject,
        token_type=JWT_TYPE_ACCESS,
        expires_in_seconds=s.jwt_access_ttl_seconds,
        extra_claims={"role": role},
        settings=s,
    )


def issue_refresh_token(*, subject: str, settings: Settings | None = None) -> tuple[str, datetime]:
    """Return `(token, expires_at)`. The plaintext token is shown to the
    client once; we persist only its hash."""
    s = settings or get_settings()
    expires_at = _now_utc() + timedelta(seconds=s.jwt_refresh_ttl_seconds)
    token = encode_jwt(
        subject=subject,
        token_type=JWT_TYPE_REFRESH,
        expires_in_seconds=s.jwt_refresh_ttl_seconds,
        settings=s,
    )
    return token, expires_at


# ── Hashing helpers (refresh tokens, API keys, generic SHA-256) ──────────────


def sha256_hex(value: str) -> str:
    """Return the hex digest of `value`. Used for refresh-token and API-key
    storage hashes."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def constant_time_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


# ── API keys ─────────────────────────────────────────────────────────────────

API_KEY_RANDOM_LEN: Final[int] = 32
"""Number of random URL-safe characters in the key body (after the prefix)."""


def generate_api_key(settings: Settings | None = None) -> tuple[str, str, str]:
    """Generate a new API key.

    Returns `(plaintext_key, prefix, key_hash)`:

    - `plaintext_key` — `"seedbank_<random>"`. Shown to the user **once**.
    - `prefix` — first 8 chars of the random portion. Stored as a non-secret
      identifier so users can tell their keys apart in the UI.
    - `key_hash` — SHA-256 hex digest of `plaintext_key`. Stored as the only
      authoritative copy.
    """
    s = settings or get_settings()
    random_part = secrets.token_urlsafe(API_KEY_RANDOM_LEN)[:API_KEY_RANDOM_LEN]
    plaintext = f"{s.api_key_prefix}{random_part}"
    return plaintext, random_part[:8], sha256_hex(plaintext)


def looks_like_api_key(value: str, settings: Settings | None = None) -> bool:
    """Cheap structural check — useful before hitting the DB on every request."""
    s = settings or get_settings()
    return value.startswith(s.api_key_prefix) and len(value) >= len(s.api_key_prefix) + 16


# ── Email-verification tokens ────────────────────────────────────────────────


def generate_verification_token() -> tuple[str, str]:
    """Return `(plaintext, sha256)`. The plaintext goes into the verification
    email; only the hash is persisted (currently in Redis with a TTL)."""
    plaintext = secrets.token_urlsafe(32)
    return plaintext, sha256_hex(plaintext)


__all__ = [
    "API_KEY_RANDOM_LEN",
    "JWT_TYPE_ACCESS",
    "JWT_TYPE_REFRESH",
    "PASSWORD_MIN_LENGTH",
    "constant_time_eq",
    "decode_jwt",
    "encode_jwt",
    "enforce_password_policy",
    "generate_api_key",
    "generate_verification_token",
    "hash_password",
    "issue_access_token",
    "issue_refresh_token",
    "looks_like_api_key",
    "sha256_hex",
    "verify_password",
]
