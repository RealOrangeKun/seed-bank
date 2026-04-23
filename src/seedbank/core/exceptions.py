"""Domain exception hierarchy.

Services raise domain errors. The router layer (``api/errors.py``) translates
them to RFC 9457 Problem Details responses. Services must never raise
``HTTPException`` directly — that would couple them to FastAPI.

Each subclass declares two class attributes consumed by the error handler:

- ``code``  — stable machine-readable enum the client can branch on
              (``forbidden``, ``not_found``, ``rate_limited``, ...). Changing
              one of these is a **breaking** API change.
- ``title`` — short human label that mirrors the HTTP status meaning
              (``Forbidden``, ``Not Found``). Safe to tweak.

The HTTP status itself lives in the handler's ``_STATUS_MAP``.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all expected domain failures."""

    code: str = "internal_error"
    title: str = "Internal Server Error"


class NotFoundError(DomainError):
    """A required entity was not found."""

    code = "not_found"
    title = "Not Found"


class ConflictError(DomainError):
    """An invariant or uniqueness constraint was violated."""

    code = "conflict"
    title = "Conflict"


class ValidationError(DomainError):
    """Input passed schema validation but failed a domain rule."""

    code = "validation_error"
    title = "Unprocessable Entity"


class AuthError(DomainError):
    """Authentication failed (bad credentials, expired token, etc.)."""

    code = "auth_error"
    title = "Unauthorized"


class ForbiddenError(DomainError):
    """Authenticated, but the actor lacks the required role or scope."""

    code = "forbidden"
    title = "Forbidden"


class RateLimitError(DomainError):
    """The actor exceeded a rate limit."""

    code = "rate_limited"
    title = "Too Many Requests"


class ExternalServiceError(DomainError):
    """An attached resource (DB, MinIO, ClickHouse, MLflow) failed."""

    code = "external_service_unavailable"
    title = "Service Unavailable"


class ModelNotReadyError(DomainError):
    """No production model is registered for the requested kind/seed type."""

    code = "model_not_ready"
    title = "Service Unavailable"
