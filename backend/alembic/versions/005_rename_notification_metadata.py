"""Rename notification metadata column to context_data

Revision ID: 005
Revises: 004
Create Date: 2025-01-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    """Rename metadata column to context_data to avoid SQLAlchemy reserved word conflict"""
    # Rename the column
    op.alter_column('notifications', 'metadata', new_column_name='context_data')


def downgrade():
    """Revert context_data column back to metadata"""
    op.alter_column('notifications', 'context_data', new_column_name='metadata')
