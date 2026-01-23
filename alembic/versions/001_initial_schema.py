"""Initial migration - create all tables."""
"""Initial migration

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enums will be auto-created by SQLAlchemy when tables are created
    # No manual creation needed - code-first approach
    
    # Create users table (supports both registered users and guests)
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('device_fingerprint', sa.String(length=255), nullable=True),
        sa.Column('is_guest', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_device_fingerprint'), 'users', ['device_fingerprint'], unique=True)
    
    # Create scan_batches table
    op.create_table(
        'scan_batches',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('status', postgresql.ENUM('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='processingstatus', create_type=True), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('processing_start_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_end_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_duration_ms', sa.Integer(), nullable=True),
        sa.Column('total_seeds', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('bad_seeds_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_confidence_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scan_batches_id'), 'scan_batches', ['id'], unique=False)
    op.create_index(op.f('ix_scan_batches_user_id'), 'scan_batches', ['user_id'], unique=False)
    op.create_index(op.f('ix_scan_batches_created_at'), 'scan_batches', ['created_at'], unique=False)
    
    # Create scan_images table
    op.create_table(
        'scan_images',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('batch_id', sa.BigInteger(), nullable=False),
        sa.Column('storage_path', sa.Text(), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['batch_id'], ['scan_batches.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scan_images_id'), 'scan_images', ['id'], unique=False)
    op.create_index(op.f('ix_scan_images_batch_id'), 'scan_images', ['batch_id'], unique=False)
    
    # Create seed_detections table
    op.create_table(
        'seed_detections',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('batch_id', sa.BigInteger(), nullable=False),
        sa.Column('image_id', sa.BigInteger(), nullable=False),
        sa.Column('quality_label', postgresql.ENUM('GOOD', 'BAD', name='qualitylabel', create_type=True), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('detection_confidence', sa.Float(), nullable=False),
        sa.Column('box_x_norm', sa.Float(), nullable=False),
        sa.Column('box_y_norm', sa.Float(), nullable=False),
        sa.Column('box_w_norm', sa.Float(), nullable=False),
        sa.Column('box_h_norm', sa.Float(), nullable=False),
        sa.Column('area', sa.Float(), nullable=True),
        sa.Column('width', sa.Float(), nullable=True),
        sa.Column('height', sa.Float(), nullable=True),
        sa.Column('aspect_ratio', sa.Float(), nullable=True),
        sa.Column('centroid_x', sa.Float(), nullable=True),
        sa.Column('centroid_y', sa.Float(), nullable=True),
        sa.Column('good_percentage', sa.Float(), nullable=True),
        sa.Column('bad_percentage', sa.Float(), nullable=True),
        sa.Column('classification_confidence', sa.Float(), nullable=True),
        sa.Column('raw_probability', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['batch_id'], ['scan_batches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['image_id'], ['scan_images.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_seed_detections_id'), 'seed_detections', ['id'], unique=False)
    op.create_index(op.f('ix_seed_detections_batch_id'), 'seed_detections', ['batch_id'], unique=False)
    op.create_index(op.f('ix_seed_detections_image_id'), 'seed_detections', ['image_id'], unique=False)
    op.create_index(op.f('ix_seed_detections_created_at'), 'seed_detections', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_seed_detections_created_at'), table_name='seed_detections')
    op.drop_index(op.f('ix_seed_detections_image_id'), table_name='seed_detections')
    op.drop_index(op.f('ix_seed_detections_batch_id'), table_name='seed_detections')
    op.drop_index(op.f('ix_seed_detections_id'), table_name='seed_detections')
    op.drop_table('seed_detections')
    
    op.drop_index(op.f('ix_scan_images_batch_id'), table_name='scan_images')
    op.drop_index(op.f('ix_scan_images_id'), table_name='scan_images')
    op.drop_table('scan_images')
    
    op.drop_index(op.f('ix_scan_batches_created_at'), table_name='scan_batches')
    op.drop_index(op.f('ix_scan_batches_user_id'), table_name='scan_batches')
    op.drop_index(op.f('ix_scan_batches_id'), table_name='scan_batches')
    op.drop_table('scan_batches')
    
    op.drop_index(op.f('ix_users_device_fingerprint'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS qualitylabel')
    op.execute('DROP TYPE IF EXISTS processingstatus')

