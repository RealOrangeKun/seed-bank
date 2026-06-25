"""Batch management service — the read + lifecycle side of ``/api/v1/batches``.

Split from :class:`AnalysisService` deliberately: writing a batch
(multipart upload, MinIO, Celery dispatch) and reading/managing one
(eager-load the nested graph, soft-delete, export detections) have nothing
in common. Two thin services beat one god class with two unrelated halves.

The deletes here are *soft* deletes (``deleted_at`` stamp) — hard delete is
forbidden on this aggregate (see ``SoftDeleteMixin``). Export is read-only.

The service raises domain exceptions only — the router maps to HTTP.
``HTTPException`` is forbidden here.
"""

from __future__ import annotations

import asyncio
import io
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from seedbank.core.config import get_settings
from seedbank.core.exceptions import NotFoundError
from seedbank.core.logging import get_logger
from seedbank.domain.user import Role

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from seedbank.core.config import Settings
    from seedbank.domain.user import AuthenticatedUser
    from seedbank.infrastructure.db.models import ScanBatch, SeedDetection
    from seedbank.infrastructure.db.repositories import (
        ScanBatchRepository,
        ScanImageRepository,
    )
    from seedbank.infrastructure.storage import MinioStorage

log = get_logger(__name__)

# Box colors by quality (RGB). Mirrors the frontend overlay palette so the
# server-rendered PNG and the interactive overlay read the same.
_QUALITY_COLORS: dict[str | None, tuple[int, int, int]] = {
    "good": (34, 160, 90),
    "bad": (200, 50, 50),
    None: (60, 130, 220),
}


def _draw_boxes(raw: bytes, detections: list) -> bytes:  # noqa: ANN001 — ORM rows
    """Burn normalized detection boxes onto an image, return PNG bytes.

    Pure/CPU-bound (runs in a thread). Coordinates are stored normalized
    (0–1); we scale to the decoded image's pixel size, so this is resolution
    independent. Line width scales with image size so boxes stay visible on
    large scans.
    """
    from PIL import Image, ImageDraw

    img = Image.open(io.BytesIO(raw)).convert("RGB")
    w, h = img.size
    draw = ImageDraw.Draw(img)
    line_width = max(2, round(min(w, h) * 0.004))

    for d in detections:
        x = float(d.box_x_norm) * w
        y = float(d.box_y_norm) * h
        bw = float(d.box_w_norm) * w
        bh = float(d.box_h_norm) * h
        color = _QUALITY_COLORS.get(d.quality, _QUALITY_COLORS[None])
        draw.rectangle([x, y, x + bw, y + bh], outline=color, width=line_width)

    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


@dataclass(frozen=True, slots=True)
class ImageUrl:
    """A presigned, browser-reachable URL for one stored scan image."""

    image_id: UUID
    url: str
    expires_at: datetime


class BatchService:
    """Read paths for ``ScanBatch`` aggregates."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        batches: ScanBatchRepository,
        images: ScanImageRepository,
        storage: MinioStorage,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.batches = batches
        self.images = images
        self.storage = storage
        self.settings = settings or get_settings()

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        page: int,
        page_size: int,
        supplier_id: UUID | None = None,
        country_code: str | None = None,
    ) -> tuple[list[tuple[ScanBatch, int]], int]:
        """Return ``(rows, total)`` for the requested page.

        Each row is a ``(batch, image_count)`` pair — ``scan_batches`` has
        no ``image_count`` column, so the repository derives it in a single
        grouped query (no N+1). ``total`` is the unpaginated count under the
        same filters so the caller can build a ``Page[BatchOut]``. ``page``
        is 1-indexed, matching the schemas' :class:`PageMeta`.
        """
        offset = (page - 1) * page_size
        rows = await self.batches.list_for_user_with_counts(
            user_id,
            limit=page_size,
            offset=offset,
            supplier_id=supplier_id,
            country_code=country_code,
        )
        total = await self.batches.count_for_user(
            user_id,
            supplier_id=supplier_id,
            country_code=country_code,
        )
        return rows, total

    async def get_for_user(
        self,
        *,
        batch_id: UUID,
        actor: AuthenticatedUser,
    ) -> ScanBatch:
        """Fetch the full nested graph for a batch the actor may read.

        - Admins use the unscoped query and may read any batch.
        - Everyone else is filtered by ``user_id`` so a user cannot
          enumerate someone else's batches.

        ``NotFoundError`` is raised both when the row is absent and when
        a non-admin caller does not own it. Leaking the difference would
        let users probe for IDs.
        """
        if actor.role is Role.ADMIN:
            row = await self.batches.get_with_full_graph(batch_id)
        else:
            row = await self.batches.get_with_images_and_detections(batch_id, actor.id)
        if row is None:
            raise NotFoundError("Batch not found.")
        return row

    async def image_urls_for_user(
        self,
        *,
        batch_id: UUID,
        actor: AuthenticatedUser,
    ) -> list[ImageUrl]:
        """Presigned GET URLs for every image in a batch the actor may read.

        Ownership is enforced exactly as in :meth:`get_for_user` (admins may
        read any batch; everyone else only their own), and the same
        ``NotFoundError``-on-miss rule applies so image IDs cannot be probed.
        Unlike :meth:`get_for_user` this does *not* load the detection graph —
        only the lightweight image rows are needed to mint URLs.
        """
        if actor.role is Role.ADMIN:
            batch = await self.batches.get(batch_id)
        else:
            batch = await self.batches.get_for_user(batch_id, actor.id)
        if batch is None:
            raise NotFoundError("Batch not found.")

        ttl = timedelta(seconds=self.settings.minio_presign_ttl_seconds)
        expires_at = datetime.now(UTC) + ttl
        images = await self.images.list_for_batch(batch_id)
        urls: list[ImageUrl] = []
        for image in images:
            url = await self.storage.presigned_get_url(
                self.settings.minio_bucket_images, image.storage_key, ttl
            )
            urls.append(ImageUrl(image_id=image.id, url=url, expires_at=expires_at))
        return urls

    async def delete_for_user(
        self,
        *,
        batch_id: UUID,
        actor: AuthenticatedUser,
    ) -> None:
        """Soft-delete a batch the actor may delete.

        Owners may delete their own batches; admins may delete any. The miss
        case raises ``NotFoundError`` (never ``ForbiddenError``) so a caller
        cannot distinguish "doesn't exist" from "exists but not yours" — same
        non-enumeration rule as :meth:`get_for_user`.

        Idempotent only at the storage layer: a second delete of an
        already-soft-deleted batch finds no live row and raises
        ``NotFoundError``, matching the read endpoints which also hide
        soft-deleted batches.
        """
        # Admins aren't scoped to ownership; resolve the owner so the
        # user-scoped repository UPDATE still matches the row.
        owner_id = await self._owner_id_for(batch_id=batch_id, actor=actor)
        deleted = await self.batches.soft_delete_for_user(batch_id, owner_id)
        if not deleted:
            raise NotFoundError("Batch not found.")
        await self.session.commit()
        log.info("batch.deleted", batch_id=str(batch_id), actor_id=str(actor.id))

    async def bulk_delete_for_user(
        self,
        *,
        batch_ids: list[UUID],
        actor: AuthenticatedUser,
    ) -> int:
        """Soft-delete every owned, still-live batch in ``batch_ids``.

        Returns the number actually deleted. Unowned / unknown / already-deleted
        IDs are silently skipped — bulk delete is best-effort by design, so a
        partially-stale selection doesn't fail the whole request. Admins may
        delete across users.

        Note: a non-admin's IDs are filtered to their own rows in the repo
        ``WHERE``; an admin's selection may span users, so we don't pre-resolve
        a single owner for them — instead we widen the scope below.
        """
        if not batch_ids:
            return 0
        # De-dupe so a repeated ID can't be counted twice and the IN-list stays
        # tight.
        unique_ids = list(dict.fromkeys(batch_ids))
        if actor.role is Role.ADMIN:
            deleted = await self.batches.soft_delete_many_any_owner(unique_ids)
        else:
            deleted = await self.batches.soft_delete_many_for_user(unique_ids, actor.id)
        await self.session.commit()
        log.info(
            "batch.bulk_deleted",
            requested=len(unique_ids),
            deleted=deleted,
            actor_id=str(actor.id),
        )
        return deleted

    async def detections_for_export(
        self,
        *,
        batch_id: UUID,
        actor: AuthenticatedUser,
    ) -> list[SeedDetection]:
        """Flat, ordered list of every detection in a batch the actor may read.

        Backs both the CSV and JSON export endpoints — the router decides the
        wire format; the service only owns access control + ordering. Ownership
        and the ``NotFoundError``-on-miss rule mirror :meth:`get_for_user`.
        """
        owner_id = await self._owner_id_for(batch_id=batch_id, actor=actor)
        return await self.batches.list_detections_for_batch(batch_id, owner_id)

    async def annotated_png_for_user(
        self,
        *,
        batch_id: UUID,
        image_id: UUID,
        actor: AuthenticatedUser,
    ) -> bytes:
        """Render the scan image with its detection boxes burned in, as PNG.

        Ownership is enforced via the full-graph load (admins any, others their
        own; ``NotFoundError`` on miss). The image bytes come from object
        storage; boxes are stored normalized (0–1) so they scale to whatever
        pixel size the stored image has. Drawing is offloaded to a thread —
        Pillow is CPU-bound and would otherwise block the event loop.
        """
        batch = await self.get_for_user(batch_id=batch_id, actor=actor)
        image = next((im for im in batch.images if im.id == image_id), None)
        if image is None:
            raise NotFoundError("Image not found.")

        raw = await self.storage.get_object(self.settings.minio_bucket_images, image.storage_key)
        detections = [d for inf in image.inferences for d in inf.detections]
        return await asyncio.to_thread(_draw_boxes, raw, detections)

    async def create_share_link(
        self,
        *,
        batch_id: UUID,
        actor: AuthenticatedUser,
    ) -> str:
        """Create (or rotate) a public share token for an owned batch.

        Returns the token. Idempotent in spirit but not in value: calling it
        again rotates the token (the old link stops working), which is the safe
        default for "re-share". Ownership enforced; ``NotFoundError`` on miss.
        """
        owner_id = await self._owner_id_for(batch_id=batch_id, actor=actor)
        token = secrets.token_urlsafe(32)
        ok = await self.batches.set_share_token(batch_id, owner_id, token)
        if not ok:
            raise NotFoundError("Batch not found.")
        await self.session.commit()
        log.info("batch.share_created", batch_id=str(batch_id))
        return token

    async def revoke_share_link(
        self,
        *,
        batch_id: UUID,
        actor: AuthenticatedUser,
    ) -> None:
        """Clear the share token so the public link stops working."""
        owner_id = await self._owner_id_for(batch_id=batch_id, actor=actor)
        ok = await self.batches.set_share_token(batch_id, owner_id, None)
        if not ok:
            raise NotFoundError("Batch not found.")
        await self.session.commit()
        log.info("batch.share_revoked", batch_id=str(batch_id))

    async def get_shared_batch(self, *, token: str) -> ScanBatch:
        """Resolve a public share token to its batch graph (no auth).

        The token is the capability — no ownership check. Raises
        ``NotFoundError`` for an unknown/revoked/deleted token so a guesser
        can't distinguish those cases.
        """
        batch = await self.batches.get_by_share_token(token)
        if batch is None:
            raise NotFoundError("Shared batch not found.")
        return batch

    async def _owner_id_for(
        self,
        *,
        batch_id: UUID,
        actor: AuthenticatedUser,
    ) -> UUID:
        """Resolve the owning ``user_id`` for a batch the actor may act on.

        For a non-admin this is just ``actor.id`` — but we still confirm the
        batch exists and is live (and owned), raising ``NotFoundError`` if not,
        so callers get a uniform miss. For an admin we look the batch up
        unscoped and return its real owner, letting the user-scoped repository
        methods operate on any batch without leaking ownership in the error.
        """
        if actor.role is Role.ADMIN:
            batch = await self.batches.get(batch_id)
            if batch is None or batch.deleted_at is not None:
                raise NotFoundError("Batch not found.")
            return batch.user_id
        batch = await self.batches.get_for_user(batch_id, actor.id)
        if batch is None:
            raise NotFoundError("Batch not found.")
        return actor.id


__all__ = ["BatchService", "ImageUrl"]
