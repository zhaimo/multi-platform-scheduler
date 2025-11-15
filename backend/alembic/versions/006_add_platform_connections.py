"""Add platform_connections table

Revision ID: 006
Revises: 005
Create Date: 2025-01-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    # Create platform_connections table using raw SQL (platformenum already exists)
    op.execute("""
        CREATE TABLE platform_connections (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            platform platformenum NOT NULL,
            platform_user_id VARCHAR(255),
            platform_username VARCHAR(255),
            access_token TEXT NOT NULL,
            refresh_token TEXT,
            token_expires_at TIMESTAMP,
            scopes JSONB DEFAULT '[]'::jsonb,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL
        )
    """)
    
    # Create indexes
    op.create_index('idx_platform_connection_user_platform', 'platform_connections', ['user_id', 'platform'], unique=True)
    op.create_index('idx_platform_connections_user_id', 'platform_connections', ['user_id'])
    op.create_index('idx_platform_connections_platform', 'platform_connections', ['platform'])


def downgrade():
    op.drop_index('idx_platform_connections_platform', table_name='platform_connections')
    op.drop_index('idx_platform_connections_user_id', table_name='platform_connections')
    op.drop_index('idx_platform_connection_user_platform', table_name='platform_connections')
    op.drop_table('platform_connections')
