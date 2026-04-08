"""Remove redundant columns and add user constraint

Revision ID: 002_remove_redundant_columns
Revises: 001_initial_schema
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_remove_redundant_columns'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add constraint to users table: Either (username OR email) OR device_fingerprint must be present
    op.create_check_constraint(
        'user_identity_required',
        'users',
        '(username IS NOT NULL OR email IS NOT NULL) OR device_fingerprint IS NOT NULL'
    )
    
    # Remove redundant columns from seed_detections
    op.drop_column('seed_detections', 'classification_confidence')
    op.drop_column('seed_detections', 'raw_probability')


def downgrade() -> None:
    # Add back the columns
    op.add_column('seed_detections', sa.Column('raw_probability', sa.Float(), nullable=True))
    op.add_column('seed_detections', sa.Column('classification_confidence', sa.Float(), nullable=True))
    
    # Remove constraint
    op.drop_constraint('user_identity_required', 'users', type_='check')

