"""Unit tests for the builder registry.

These tests do **not** trigger autodiscovery — they exercise the decorator
and lookup against an isolated registry state via ``_reset_for_tests``.
"""

from __future__ import annotations

import pytest

from seedbank.infrastructure.ml import registry


@pytest.fixture(autouse=True)
def _isolate_registry() -> None:
    registry._reset_for_tests()
    # Pretend autodiscovery already ran so tests don't import the builder
    # files (which need torch).
    registry._DISCOVERED = True
    yield
    registry._reset_for_tests()


def test_register_and_get() -> None:
    @registry.register_builder("dummy-v1")
    def build() -> object:
        return object()

    assert registry.get_builder("dummy-v1") is build


def test_list_builders_returns_sorted() -> None:
    @registry.register_builder("z-v1")
    def build_z() -> object:
        return object()

    @registry.register_builder("a-v1")
    def build_a() -> object:
        return object()

    assert registry.list_builders() == ["a-v1", "z-v1"]


def test_duplicate_key_raises() -> None:
    @registry.register_builder("dup-v1")
    def first() -> object:
        return object()

    with pytest.raises(registry.BuilderAlreadyRegisteredError):
        @registry.register_builder("dup-v1")
        def second() -> object:  # noqa: F811
            return object()


def test_unknown_key_raises() -> None:
    with pytest.raises(registry.BuilderNotFoundError):
        registry.get_builder("nope")


def test_empty_key_rejected() -> None:
    with pytest.raises(ValueError):
        registry.register_builder("")(lambda: object())


def test_re_registering_same_function_is_idempotent() -> None:
    """Re-importing a builder file (e.g. via reload) shouldn't blow up."""

    def build() -> object:
        return object()

    registry.register_builder("idem-v1")(build)
    # Same function, same key — must be a no-op, not an error.
    registry.register_builder("idem-v1")(build)
    assert registry.get_builder("idem-v1") is build
