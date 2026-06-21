"""``/api/v1/analytics`` — aggregated, user-scoped analytics.

A single GET returns headline totals, a per-day activity trend, a per-seed-type
good/bad split, and a confidence histogram — everything the dashboard's
analytics view needs in one round trip. Computed from the OLTP tables and scoped
to the caller (admins see their own here; cross-user analytics is out of scope).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from seedbank.api.deps import AnalyticsServiceDep, CurrentUser
from seedbank.schemas.analytics import AnalyticsOut
from seedbank.schemas.common import Envelope

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("", response_model=Envelope[AnalyticsOut])
async def get_analytics(
    actor: CurrentUser,
    service: AnalyticsServiceDep,
    window_days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> Envelope[AnalyticsOut]:
    """Aggregated analytics for the caller over the trailing ``window_days``.

    The trend line spans the window (zero-filled per day); totals,
    type split, and confidence histogram cover the user's whole live history.
    """
    data = await service.summary(user_id=actor.id, window_days=window_days)
    return Envelope[AnalyticsOut](data=data)


__all__ = ["router"]
