"""Domain-error → HTTP-response mapping.

Services raise `DomainError` subclasses; the router layer never sees raw DB
or backend exceptions. This module is the single place where the mapping
lives, so when we add a new exception we know exactly where to register
its HTTP face.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from seedbank.core.exceptions import (
    AuthError,
    ConflictError,
    DomainError,
    ExternalServiceError,
    ForbiddenError,
    ModelNotReadyError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from seedbank.core.logging import get_logger

log = get_logger(__name__)

_STATUS_MAP: dict[type[DomainError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    ValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    AuthError: status.HTTP_401_UNAUTHORIZED,
    ForbiddenError: status.HTTP_403_FORBIDDEN,
    RateLimitError: status.HTTP_429_TOO_MANY_REQUESTS,
    ExternalServiceError: status.HTTP_503_SERVICE_UNAVAILABLE,
    ModelNotReadyError: status.HTTP_503_SERVICE_UNAVAILABLE,
}


def _payload(exc: DomainError) -> dict[str, str]:
    return {"error": exc.__class__.__name__, "detail": str(exc)}


def install_error_handlers(app: FastAPI) -> None:
    """Wire one handler per domain error class plus a fallback for the base
    class. Order matters: more-specific subclasses first."""

    for exc_cls, http_status in _STATUS_MAP.items():
        async def _handler(  # type: ignore[no-redef]
            _: Request, exc: DomainError, _status: int = http_status
        ) -> JSONResponse:
            log.info("domain_error", error=exc.__class__.__name__, detail=str(exc))
            return JSONResponse(status_code=_status, content=_payload(exc))

        app.add_exception_handler(exc_cls, _handler)

    async def _fallback(_: Request, exc: DomainError) -> JSONResponse:
        # Subclasses of DomainError not in the map fall through here.
        log.warning("unmapped_domain_error", error=exc.__class__.__name__, detail=str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=_payload(exc)
        )

    app.add_exception_handler(DomainError, _fallback)
