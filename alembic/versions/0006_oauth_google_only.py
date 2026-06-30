"""tighten oauth provider constraint to google-only

The GitHub OAuth provider was removed alongside the personal API-key feature
(see ``0005_drop_api_keys.py``). Only Google social login remains, so the
``oauth_accounts.provider_supported`` CHECK constraint — originally
``provider IN ('google', 'github')`` from ``0001_baseline.py`` — is tightened to
``provider IN ('google')`` to match the ORM model and reject any provider that
can no longer authenticate.

The upgrade validates existing rows; it fails if a row still has
``provider = 'github'`` (none exist in practice — GitHub OAuth was never used in
prod and stored no usable tokens). ``downgrade`` restores the permissive form.

Hand-rolled. Mirrors the constraint defined in ``0001_baseline.py``.

Revision ID: 0006_oauth_google_only
Revises: 0005_drop_api_keys
Create Date: 2026-06-30 00:00:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "0006_oauth_google_only"
down_revision = "0005_drop_api_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("provider_supported", "oauth_accounts", type_="check")
    op.create_check_constraint("provider_supported", "oauth_accounts", "provider IN ('google')")


def downgrade() -> None:
    op.drop_constraint("provider_supported", "oauth_accounts", type_="check")
    op.create_check_constraint(
        "provider_supported", "oauth_accounts", "provider IN ('google', 'github')"
    )
