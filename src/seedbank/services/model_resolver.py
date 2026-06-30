"""ModelResolver — picks the model for ``(kind, seed_type_id)`` per request.

The live inference path needs exactly one model per segment. Resolution is:

* the ``production`` ``model_artifacts`` row for the segment;
* when the seed type has no model of its own, fall back to the global
  (seed-type-agnostic) ``production`` row — so per-seed-type promotion is
  *optional*: a deployment can promote a single global model and every scan
  routes to it, including the mobile point-and-shoot flow which never sends a
  seed type. A typed scan still prefers its own model when one exists.
* otherwise raise ``ModelNotReadyError`` — surfaced to the client as 503.
"""

from __future__ import annotations

from uuid import UUID

from seedbank.core.exceptions import ModelNotReadyError
from seedbank.infrastructure.db.enums import ModelKind
from seedbank.infrastructure.db.repositories import ModelArtifactRepository


class ModelResolver:
    def __init__(self, *, models: ModelArtifactRepository) -> None:
        self.models = models

    async def select_model(
        self,
        *,
        kind: ModelKind,
        seed_type_id: UUID | None,
    ) -> UUID:
        prod = await self.models.get_production(kind, seed_type_id)
        if prod is None and seed_type_id is not None:
            prod = await self.models.get_production(kind, None)
        if prod is not None:
            return prod.id

        raise ModelNotReadyError(
            f"No production model for kind={kind.value} seed_type_id={seed_type_id}"
        )


__all__ = ["ModelResolver"]
