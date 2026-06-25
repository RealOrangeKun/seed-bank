"""``/api/v1/shared/{token}`` — public, unauthenticated batch reports.

The share token is the capability: anyone holding it can read the batch's
results. No ``CurrentUser`` dependency here, so the route is reachable without a
bearer token. The response shape (:class:`SharedBatchOut`) deliberately omits
owner/user identifiers so a link never leaks who ran the scan.
"""

from __future__ import annotations

from fastapi import APIRouter

from seedbank.api.deps import BatchServiceDep
from seedbank.schemas.analysis import SharedBatchOut
from seedbank.schemas.common import Envelope

router = APIRouter(prefix="/shared", tags=["shared"])


@router.get("/{token}", response_model=Envelope[SharedBatchOut])
async def get_shared_batch(
    token: str,
    service: BatchServiceDep,
) -> Envelope[SharedBatchOut]:
    """Read-only public view of a shared batch. 404 if the token is unknown,
    revoked, or the batch was deleted."""
    batch = await service.get_shared_batch(token=token)
    out = SharedBatchOut.model_validate(batch, from_attributes=True)
    out = out.model_copy(update={"image_count": len(out.images)})
    return Envelope[SharedBatchOut](data=out)


__all__ = ["router"]
