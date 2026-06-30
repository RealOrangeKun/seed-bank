"""Unit tests for :class:`ModelResolver` — production model selection.

The resolver replaced the old traffic-split A/B router. It now does one thing:
resolve the ``production`` model for a segment, falling back to the global
(seed-type-agnostic) production model, else raising ``ModelNotReadyError``.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from seedbank.core.exceptions import ModelNotReadyError
from seedbank.infrastructure.db.enums import ModelKind
from seedbank.services.model_resolver import ModelResolver

pytestmark = pytest.mark.unit


class _Row:
    """Minimal stand-in for a ``ModelArtifact`` row — only ``.id`` is read."""

    def __init__(self, model_id: UUID) -> None:
        self.id = model_id


class _FakeModels:
    """Records calls and answers ``get_production`` from a fixed mapping."""

    def __init__(self, mapping: dict[tuple[ModelKind, UUID | None], _Row]) -> None:
        self._mapping = mapping
        self.calls: list[tuple[ModelKind, UUID | None]] = []

    async def get_production(self, kind: ModelKind, seed_type_id: UUID | None) -> _Row | None:
        self.calls.append((kind, seed_type_id))
        return self._mapping.get((kind, seed_type_id))


async def test_resolves_seed_type_production_model() -> None:
    seed = uuid4()
    row = _Row(uuid4())
    resolver = ModelResolver(models=_FakeModels({(ModelKind.DETECTION, seed): row}))  # type: ignore[arg-type]

    chosen = await resolver.select_model(kind=ModelKind.DETECTION, seed_type_id=seed)

    assert chosen == row.id


async def test_falls_back_to_global_production_model() -> None:
    seed = uuid4()
    global_row = _Row(uuid4())
    models = _FakeModels({(ModelKind.DETECTION, None): global_row})

    resolver = ModelResolver(models=models)  # type: ignore[arg-type]
    chosen = await resolver.select_model(kind=ModelKind.DETECTION, seed_type_id=seed)

    assert chosen == global_row.id
    # Seed-specific lookup first, then the global fallback.
    assert models.calls == [
        (ModelKind.DETECTION, seed),
        (ModelKind.DETECTION, None),
    ]


async def test_raises_when_nothing_promoted() -> None:
    resolver = ModelResolver(models=_FakeModels({}))  # type: ignore[arg-type]

    with pytest.raises(ModelNotReadyError):
        await resolver.select_model(kind=ModelKind.CLASSIFICATION, seed_type_id=None)
