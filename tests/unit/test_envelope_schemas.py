"""Unit tests for the cross-cutting envelope schemas.

These tests pin the *shape* of ``Envelope[T]``, ``Page[T]``, ``PageMeta``,
``Problem``, ``ProblemFieldError`` and the ``paginate`` helper. No app, no
DB, no HTTP — pure Pydantic. The HTTP-level contract is exercised
separately under ``tests/e2e/test_envelopes.py``.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from seedbank.schemas.common import (
    Envelope,
    Page,
    PageMeta,
    Problem,
    ProblemFieldError,
    paginate,
)

pytestmark = pytest.mark.unit


class _Item(BaseModel):
    """Trivial inner schema used as ``T`` for the generics below."""

    id: int
    name: str


# ── Envelope[T] ─────────────────────────────────────────────────────────────


def test_envelope_serialises_single_resource_under_data_key() -> None:
    env = Envelope[_Item](data=_Item(id=1, name="alpha"))

    assert env.model_dump() == {"data": {"id": 1, "name": "alpha"}}


def test_envelope_rejects_payload_without_data() -> None:
    with pytest.raises(ValidationError):
        Envelope[_Item].model_validate({})


# ── PageMeta ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("field", "value"),
    [("page", 0), ("page_size", 0), ("total", -1)],
)
def test_page_meta_rejects_below_minimum_values(field: str, value: int) -> None:
    base = {"page": 1, "page_size": 10, "total": 0, "has_more": False}
    base[field] = value

    with pytest.raises(ValidationError):
        PageMeta.model_validate(base)


# ── paginate(): has_more boundary cases ─────────────────────────────────────


def test_paginate_empty_collection_reports_no_more_pages() -> None:
    page = paginate([], total=0, page=1, page_size=50)

    assert page.data == []
    assert page.meta.total == 0
    assert page.meta.has_more is False


def test_paginate_marks_has_more_true_when_more_rows_remain() -> None:
    items = [_Item(id=i, name=str(i)) for i in range(50)]
    page = paginate(items, total=137, page=1, page_size=50)

    assert page.meta.has_more is True
    assert page.meta.total == 137


def test_paginate_marks_has_more_false_on_last_page_exact_fit() -> None:
    """``has_more`` flips to ``False`` when ``page * page_size == total``."""
    items = [_Item(id=i, name=str(i)) for i in range(50)]
    page = paginate(items, total=100, page=2, page_size=50)

    assert page.meta.has_more is False


def test_paginate_marks_has_more_false_on_last_page_partial_fit() -> None:
    """Partial last page: ``page * page_size > total``."""
    items = [_Item(id=i, name=str(i)) for i in range(7)]
    page = paginate(items, total=57, page=2, page_size=50)

    assert page.meta.has_more is False


# ── Problem (RFC 9457) ──────────────────────────────────────────────────────


def test_problem_minimal_required_fields_only() -> None:
    p = Problem(
        type="https://seedbank.dev/problems/not_found",
        title="Not Found",
        status=404,
        code="not_found",
    )

    body = p.model_dump(exclude_none=True)
    assert body["status"] == 404
    assert body["code"] == "not_found"
    assert "errors" not in body
    assert "request_id" not in body


def test_problem_validation_error_carries_per_field_errors() -> None:
    p = Problem(
        type="https://seedbank.dev/problems/validation_error",
        title="Validation Failed",
        status=422,
        code="validation_error",
        errors=[
            ProblemFieldError(field="password", message="too short", code="value_error"),
        ],
    )

    body = p.model_dump(exclude_none=True)
    assert body["errors"] == [{"field": "password", "message": "too short", "code": "value_error"}]


def test_problem_allows_extension_fields() -> None:
    """``model_config = ConfigDict(extra="allow")`` so handlers can attach
    domain-specific extensions without schema churn."""
    p = Problem.model_validate(
        {
            "type": "https://seedbank.dev/problems/forbidden",
            "title": "Forbidden",
            "status": 403,
            "code": "forbidden",
            "required_role": "admin",
        }
    )

    body = p.model_dump(exclude_none=True)
    assert body["required_role"] == "admin"
