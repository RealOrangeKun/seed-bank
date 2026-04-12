"""API-key service — issue, list, revoke. Hash-at-rest enforced.

The plaintext key is shown to the user **once** on issuance and never
retrievable from the API again. We persist only:

- `key_hash` — SHA-256 of the plaintext (the credential lookup column).
- `prefix` — first 8 chars of the random portion (a non-secret identifier so
  users can tell their keys apart in the UI / logs).

Lookups go via `ApiKeyRepository.get_active_by_hash`, which already filters
by `revoked_at IS NULL` and `expires_at > now()`.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from seedbank.core.config import Settings
from seedbank.core.exceptions import NotFoundError
from seedbank.core.security import generate_api_key
from seedbank.infrastructure.db.models import ApiKey, AuditLog
from seedbank.infrastructure.db.repositories import ApiKeyRepository


class ApiKeyService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        api_keys: ApiKeyRepository,
        settings: Settings,
    ) -> None:
        self.session = session
        self.api_keys = api_keys
        self.settings = settings

    async def create(
        self,
        *,
        user_id: UUID,
        name: str,
        scopes: list[str],
        expires_at: datetime | None,
        ip: str | None = None,
    ) -> tuple[ApiKey, str]:
        """Issue a fresh key. Returns `(record, plaintext)`. The plaintext is
        meant for the response and must not be persisted anywhere else."""
        plaintext, prefix, key_hash = generate_api_key(self.settings)
        record = ApiKey(
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            prefix=prefix,
            scopes=scopes,
            expires_at=expires_at,
        )
        await self.api_keys.add(record)
        self.session.add(
            AuditLog(
                actor_id=user_id,
                action="api_key.create",
                target_type="apikey",
                target_id=str(record.id),
                audit_metadata={"name": name, "scopes": scopes},
                ip=ip,
            )
        )
        await self.session.commit()
        return record, plaintext

    async def list_for_user(self, user_id: UUID) -> list[ApiKey]:
        return await self.api_keys.list_for_user(user_id)

    async def revoke(
        self, *, user_id: UUID, key_id: UUID, ip: str | None = None
    ) -> None:
        revoked = await self.api_keys.revoke(key_id, user_id)
        if not revoked:
            raise NotFoundError("API key not found or already revoked.")
        self.session.add(
            AuditLog(
                actor_id=user_id,
                action="api_key.revoke",
                target_type="apikey",
                target_id=str(key_id),
                ip=ip,
            )
        )
        await self.session.commit()


__all__ = ["ApiKeyService"]
