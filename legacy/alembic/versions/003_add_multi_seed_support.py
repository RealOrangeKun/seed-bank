"""add multi-seed support

Revision ID: 003_add_multi_seed_support
Revises: 002_remove_redundant_columns
Create Date: 2026-02-04 16:35:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_add_multi_seed_support'
down_revision = '002_remove_redundant_columns'
branch_labels = None
depends_on = None


def upgrade():
    # Create seed_catalog table
    op.create_table(
        'seed_catalog',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_seed_catalog_id'), 'seed_catalog', ['id'], unique=False)
    op.create_index(op.f('ix_seed_catalog_name'), 'seed_catalog', ['name'], unique=False)

    # Create ai_models table
    op.create_table(
        'ai_models',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('default_threshold', sa.Float(), nullable=False),
        sa.Column('seed_type_id', sa.BigInteger(), nullable=True),
        sa.Column('model_path', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.CheckConstraint("type IN ('detection', 'quality')", name='valid_model_type'),
        sa.ForeignKeyConstraint(['seed_type_id'], ['seed_catalog.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_models_id'), 'ai_models', ['id'], unique=False)
    op.create_index(op.f('ix_ai_models_is_active'), 'ai_models', ['is_active'], unique=False)
    op.create_index(op.f('ix_ai_models_seed_type_id'), 'ai_models', ['seed_type_id'], unique=False)

    # Add seed_type_id to seed_detections table
    op.add_column('seed_detections', sa.Column('seed_type_id', sa.BigInteger(), nullable=True))
    op.create_index(op.f('ix_seed_detections_seed_type_id'), 'seed_detections', ['seed_type_id'], unique=False)
    op.create_foreign_key('fk_seed_detections_seed_type', 'seed_detections', 'seed_catalog', ['seed_type_id'], ['id'])

    # Insert initial seed types
    op.execute("""
        INSERT INTO seed_catalog (id, name) VALUES 
        (1, 'maize'),
        (2, 'coffee')
    """)

    # Insert initial AI models
    op.execute("""
        INSERT INTO ai_models (name, type, version, is_active, default_threshold, seed_type_id, model_path) VALUES 
        ('FasterRCNN_ResNet50_Final_Combined', 'detection', 'v1', true, 0.0, NULL, 'models/FasterRCNN_ResNet50_Final_Combined.pth'),
        ('ResNet18_Coffee_Quality_v3', 'quality', 'v3', true, 0.0, 2, 'models/ResNet18_COFFEE_BEANS_V3.pth'),
        ('ResNet18_Maize_Quality_v4', 'quality', 'v4', true, 5.0, 1, 'models/ResNet18_maize_Transfer_learning_wCBAM&GMP_smallerStride_Hybrid_v4.pth')
    """)


def downgrade():
    # Remove foreign key and column from seed_detections
    op.drop_constraint('fk_seed_detections_seed_type', 'seed_detections', type_='foreignkey')
    op.drop_index(op.f('ix_seed_detections_seed_type_id'), table_name='seed_detections')
    op.drop_column('seed_detections', 'seed_type_id')

    # Drop ai_models table
    op.drop_index(op.f('ix_ai_models_seed_type_id'), table_name='ai_models')
    op.drop_index(op.f('ix_ai_models_is_active'), table_name='ai_models')
    op.drop_index(op.f('ix_ai_models_id'), table_name='ai_models')
    op.drop_table('ai_models')

    # Drop seed_catalog table
    op.drop_index(op.f('ix_seed_catalog_name'), table_name='seed_catalog')
    op.drop_index(op.f('ix_seed_catalog_id'), table_name='seed_catalog')
    op.drop_table('seed_catalog')
