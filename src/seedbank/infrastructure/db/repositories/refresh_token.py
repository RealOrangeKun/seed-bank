"""Refresh-token repository.

Refresh tokens are stored as a salted hash, never the raw value. The repo
exposes:

- `get_active_by_hash` — used at refresh time to find a valid (non-revoked,
  non-expired) token; the partial unique on `(token_hash) WHERE revoked_at
  IS NULL` makes this point-look-up cheap and serves as replay detection.
- `rotate` — atomic mark-revoked + link to the replacement token, in a
  single statement, so a concurrent refresh sees one or the other side of
  the rotation but not a half-applied state.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update

from seedbank.infrastructure.db.models import RefreshToken

from .base import Repository


class RefreshTokenRepository(Repository[RefreshToken]):
    model = RefreshToken

    async def get_active_by_hash(self, token_hash: str) -> RefreshToken | None:
        now = datetime.now(tz=UTC)
        stmt = (
            select(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def rotate(self, old_id: UUID, new_id: UUID) -> int:
        """Atomically revoke `old_id` and link it to `new_id`. Returns the
        affected row count: 0 means the old token was already revoked
        (replay attempt — caller should treat as auth failure)."""
        now = datetime.now(tz=UTC)
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.id == old_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now, replaced_by_id=new_id)
        )
        result = await self.session.execute(stmt)
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def revoke_all_for_user(self, user_id: UUID) -> int:
        """Force-logout — used on password change or admin action."""
        now = datetime.now(tz=UTC)
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        result = await self.session.execute(stmt)
        return result.rowcount or 0  # type: ignore[attr-defined]
