"""Factory_boy factories for the test suite.

Per the testing skill: tests don't construct domain objects with positional
literals — factories are the single place that knows which fields are
required to build a valid instance.
"""

from __future__ import annotations

from tests.factories.user import (
    DEFAULT_TEST_PASSWORD,
    UserFactory,
    make_user,
)

__all__ = ["DEFAULT_TEST_PASSWORD", "UserFactory", "make_user"]
