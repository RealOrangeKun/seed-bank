"""add share_token to scan_batches

Revision ID: 004_add_share_token
Revises: 003_add_multi_seed_support
Create Date: 2026-06-21 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004_add_share_token'
down_revision = '003_add_multi_seed_support'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('scan_batches', sa.Column('share_token', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_scan_batches_share_token'), 'scan_batches', ['share_token'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_scan_batches_share_token'), table_name='scan_batches')
    op.drop_column('scan_batches', 'share_token')
