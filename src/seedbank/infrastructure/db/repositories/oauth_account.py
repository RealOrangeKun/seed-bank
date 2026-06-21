"""OAuth-account repository."""

from __future__ import annotations

from sqlalchemy import select

from seedbank.infrastructure.db.models import OAuthAccount

from .base import Repository


class OAuthAccountRepository(Repository[OAuthAccount]):
    model = OAuthAccount

    async def get_by_provider_subject(
        self, provider: str, provider_subject: str
    ) -> OAuthAccount | None:
        stmt = select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_subject == provider_subject,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
