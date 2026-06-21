"""Cross-cutting response shapes.

Every API response — success or error — is wrapped in one of these:

- ``Envelope[T]``  → ``{"data": <single resource>}``
- ``Page[T]``      → ``{"data": [...], "meta": {page, page_size, total, has_more}}``
- ``Problem``      → RFC 9457 Problem Details (errors only; emitted by
                     ``api/errors.py``, not returned from routers directly)

Health and Prometheus endpoints are exempt — Kubernetes probes and the
metrics scraper expect raw shapes, and breaking that contract is more
expensive than the inconsistency.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class Envelope(BaseModel, Generic[T]):
    """Wrapper for a single resource — ``{"data": ...}``."""

    data: T


class PageMeta(BaseModel):
    """Pagination cursor metadata. ``page`` is 1-indexed."""

    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)
    has_more: bool


class Page(BaseModel, Generic[T]):
    """Wrapper for a paginated collection — ``{"data": [...], "meta": ...}``."""

    data: list[T]
    meta: PageMeta


def paginate(items: list[T], *, total: int, page: int, page_size: int) -> Page[T]:
    """Build a ``Page[T]`` from a slice already fetched by the service layer.

    ``total`` is the unpaginated count; ``has_more`` is derived (cheaper than
    asking the caller). The caller is responsible for fetching exactly one
    page of ``items`` (length ≤ ``page_size``).
    """
    return Page[T](
        data=items,
        meta=PageMeta(
            page=page,
            page_size=page_size,
            total=total,
            has_more=page * page_size < total,
        ),
    )


# ── RFC 9457 Problem Details ─────────────────────────────────────────────────


class ProblemFieldError(BaseModel):
    """One field-level error inside a 422 ``Problem.errors`` array."""

    field: str
    message: str
    code: str


class Problem(BaseModel):
    """RFC 9457 Problem Details + extensions.

    Standard fields (``type``, ``title``, ``status``, ``detail``, ``instance``)
    plus three extensions consumers can rely on:

    - ``code``       — stable machine-readable enum (snake_case). Changes are
                       breaking for clients.
    - ``request_id`` — correlation id; matches the ``X-Request-ID`` header.
    - ``errors``     — present on 422 with one entry per failing field.

    Emitted with Content-Type ``application/problem+json``. This schema is
    here only so the OpenAPI document advertises the shape; the actual JSON
    is built in ``api/errors.py`` so we never accidentally box-and-unbox.
    """

    model_config = ConfigDict(extra="allow")

    type: str
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    code: str
    request_id: str | None = None
    errors: list[ProblemFieldError] | None = None


__all__ = [
    "Envelope",
    "Page",
    "PageMeta",
    "Problem",
    "ProblemFieldError",
    "paginate",
]
