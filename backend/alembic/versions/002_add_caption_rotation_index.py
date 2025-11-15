"""add caption rotation index to schedules

Revision ID: 002
Revises: 001
Create Date: 2025-01-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add caption_rotation_index column to schedules table
    op.add_column('schedules', sa.Column('caption_rotation_index', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    # Remove caption_rotation_index column from schedules table
    op.drop_column('schedules', 'caption_rotation_index')
