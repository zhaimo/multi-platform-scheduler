"""add twitter to platform enum

Revision ID: 007
Revises: 006
Create Date: 2025-11-13

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 'twitter' to the platformenum type (lowercase to match existing values)
    op.execute("ALTER TYPE platformenum ADD VALUE IF NOT EXISTS 'twitter'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values easily
    # This would require recreating the enum type
    pass
