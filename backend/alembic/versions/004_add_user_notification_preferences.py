"""add user notification preferences

Revision ID: 004
Revises: 003
Create Date: 2024-01-15 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if column exists before adding (in case it was already added in initial migration)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    if 'notification_preferences' not in columns:
        # Add notification_preferences column to users table
        op.add_column(
            'users',
            sa.Column(
                'notification_preferences',
                postgresql.JSON(astext_type=sa.Text()),
                nullable=False,
                server_default='{}'
            )
        )


def downgrade() -> None:
    # Remove notification_preferences column
    op.drop_column('users', 'notification_preferences')
