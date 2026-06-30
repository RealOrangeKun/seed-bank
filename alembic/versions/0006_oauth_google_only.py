"""tighten oauth provider constraint to google-only

The GitHub OAuth provider was removed alongside the personal API-key feature
(see ``0005_drop_api_keys.py``). Only Google social login remains, so the
``oauth_accounts`` provider CHECK constraint — originally
``provider IN ('google', 'github')`` from ``0001_baseline.py`` — is tightened to
``provider IN ('google')`` to match the ORM model and reject any provider that
can no longer authenticate.

Name quirk: ``0001_baseline.py`` passed the *already-expanded* name
``ck_oauth_accounts_provider_supported`` to ``CheckConstraint(name=...)``, and the
metadata naming convention (``ck_%(table_name)s_%(constraint_name)s``) prefixed it
again — so the constraint actually lives in the database as
``ck_oauth_accounts_ck_oauth_accounts_provider_supported``. We drop it by that real
name and recreate the tightened constraint via ``create_check_constraint``, which
yields the convention-correct ``ck_oauth_accounts_provider_supported`` that the ORM
model now expects (so future autogenerate sees no drift).

The upgrade fails if a row still has ``provider = 'github'`` (none exist in
practice — GitHub OAuth was never used in prod and stored no usable tokens).
``downgrade`` restores the permissive predicate under the original doubled name.

Hand-rolled.

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

# The literal name the baseline left in the database (convention applied twice).
_BASELINE_NAME = "ck_oauth_accounts_ck_oauth_accounts_provider_supported"


def upgrade() -> None:
    op.execute(f"ALTER TABLE oauth_accounts DROP CONSTRAINT {_BASELINE_NAME}")
    op.create_check_constraint("provider_supported", "oauth_accounts", "provider IN ('google')")


def downgrade() -> None:
    op.drop_constraint("provider_supported", "oauth_accounts", type_="check")
    op.execute(
        f"ALTER TABLE oauth_accounts ADD CONSTRAINT {_BASELINE_NAME} "
        "CHECK (provider IN ('google', 'github'))"
    )
