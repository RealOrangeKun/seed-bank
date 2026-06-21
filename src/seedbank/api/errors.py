"""Domain-error → RFC 9457 Problem Details mapping.

Every error response — domain, validation, rate-limit, fallback — is built
through ``build_problem`` so the wire format is consistent:

    Content-Type: application/problem+json

    {
        "type":       "https://seedbank.dev/problems/forbidden",
        "title":      "Forbidden",
        "status":     403,
        "detail":     "Requires admin or one of roles: ai_developer.",
        "instance":   "/api/v1/models",
        "code":       "forbidden",
        "request_id": "01JK3...",
        "errors":     [...]   # 422 only
    }

The ``code`` / ``title`` come from the exception class (see
``core/exceptions.py``); the HTTP status from ``_STATUS_MAP``; the
``request_id`` from the structlog contextvar bound by ``RequestIdMiddleware``.

Routers and services keep raising ``DomainError`` subclasses. Nothing here
should ever leak through ``HTTPException``.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
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

PROBLEM_TYPE_BASE = "https://seedbank.dev/problems"
PROBLEM_CONTENT_TYPE = "application/problem+json"

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


def _request_id() -> str | None:
    """Read the request id bound by ``RequestIdMiddleware``. Returns None if
    we're somehow outside a request scope (shouldn't happen in practice)."""
    return structlog.contextvars.get_contextvars().get("request_id")


def build_problem(
    *,
    request: Request,
    status_code: int,
    code: str,
    title: str,
    detail: str | None = None,
    errors: list[dict[str, Any]] | None = None,
    extra_headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Construct a Problem Details JSONResponse. Single source of truth for
    every error shape on the wire."""
    body: dict[str, Any] = {
        "type": f"{PROBLEM_TYPE_BASE}/{code}",
        "title": title,
        "status": status_code,
        "code": code,
        "instance": request.url.path,
    }
    if detail is not None:
        body["detail"] = detail
    rid = _request_id()
    if rid is not None:
        body["request_id"] = rid
    if errors:
        body["errors"] = errors

    headers = {"Content-Type": PROBLEM_CONTENT_TYPE}
    if extra_headers:
        headers.update(extra_headers)
    return JSONResponse(status_code=status_code, content=body, headers=headers)


def _problem_for_domain_error(request: Request, exc: DomainError, status_code: int) -> JSONResponse:
    return build_problem(
        request=request,
        status_code=status_code,
        code=exc.code,
        title=exc.title,
        detail=str(exc) or None,
    )


def install_error_handlers(app: FastAPI) -> None:
    """Wire one handler per domain error class plus a fallback for the base
    class, plus the Pydantic validation handler. Order matters: more-specific
    subclasses are registered first."""

    for exc_cls, http_status in _STATUS_MAP.items():

        async def _handler(
            request: Request,
            exc: DomainError,
            _status: int = http_status,
        ) -> JSONResponse:
            log.info(
                "domain_error",
                error=exc.__class__.__name__,
                code=exc.code,
                detail=str(exc),
            )
            return _problem_for_domain_error(request, exc, _status)

        app.add_exception_handler(exc_cls, _handler)  # type: ignore[arg-type]

    async def _fallback(request: Request, exc: DomainError) -> JSONResponse:
        # Subclasses of DomainError not in the map fall through here.
        log.warning(
            "unmapped_domain_error",
            error=exc.__class__.__name__,
            code=exc.code,
            detail=str(exc),
        )
        return _problem_for_domain_error(request, exc, status.HTTP_500_INTERNAL_SERVER_ERROR)

    app.add_exception_handler(DomainError, _fallback)  # type: ignore[arg-type]

    async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Pydantic 422 → Problem Details with ``errors[]`` per field.

        Each Pydantic error has shape ``{"loc": [...], "msg": ..., "type": ...}``;
        we translate ``loc`` to a dotted path (skipping the root segment which
        is always ``"body"`` / ``"query"`` / ``"path"``) and surface ``type``
        as the per-field ``code``.
        """
        field_errors: list[dict[str, Any]] = []
        for err in exc.errors():
            loc = err.get("loc", ())
            # Drop the root segment ("body", "query", "path", ...) so the
            # field path is meaningful to the client.
            path_parts = [str(p) for p in loc[1:]] if len(loc) > 1 else [str(p) for p in loc]
            field_errors.append(
                {
                    "field": ".".join(path_parts) or "<root>",
                    "message": err.get("msg", "Invalid value."),
                    "code": err.get("type", "invalid"),
                }
            )
        log.info("validation_error", n_errors=len(field_errors))
        return build_problem(
            request=request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="validation_error",
            title="Unprocessable Entity",
            detail="Request payload failed validation.",
            errors=field_errors,
        )

    app.add_exception_handler(RequestValidationError, _validation_handler)  # type: ignore[arg-type]


__all__ = [
    "PROBLEM_CONTENT_TYPE",
    "PROBLEM_TYPE_BASE",
    "build_problem",
    "install_error_handlers",
]
