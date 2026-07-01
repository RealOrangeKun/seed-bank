"""add scan_batches.result_video_key for the annotated YOLO video path

The video analyze path samples a clip, runs the YOLO one-shot detector on each
frame, burns the detection boxes into a re-encoded H.264 mp4, and stores it in
MinIO. ``result_video_key`` holds that object key (NULL for image batches); the
batch-detail / shared responses turn it into a presigned playback URL.

Hand-rolled.

Revision ID: 0007_scan_batch_result_video
Revises: 0006_oauth_google_only
Create Date: 2026-07-01 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_scan_batch_result_video"
down_revision = "0006_oauth_google_only"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scan_batches",
        sa.Column("result_video_key", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scan_batches", "result_video_key")
