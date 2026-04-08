"""Domain exception hierarchy.

Services raise domain errors. The router layer (`api/errors.py`) translates them
to `HTTPException`. Services must never raise `HTTPException` directly — that
would couple them to FastAPI.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all expected domain failures."""


class NotFoundError(DomainError):
    """A required entity was not found."""


class ConflictError(DomainError):
    """An invariant or uniqueness constraint was violated."""


class ValidationError(DomainError):
    """Input passed schema validation but failed a domain rule."""


class AuthError(DomainError):
    """Authentication failed (bad credentials, expired token, etc.)."""


class ForbiddenError(DomainError):
    """Authenticated, but the actor lacks the required role or scope."""


class RateLimitError(DomainError):
    """The actor exceeded a rate limit."""


class ExternalServiceError(DomainError):
    """An attached resource (DB, MinIO, ClickHouse, MLflow) failed."""


class ModelNotReadyError(DomainError):
    """No production model is registered for the requested kind/seed type."""
