"""Fix platform enum casing - standardize to uppercase

Revision ID: 008
Revises: 007
Create Date: 2025-11-13

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The database currently has mixed case values
    # We need to standardize everything to UPPERCASE to match existing values
    
    # First, update any existing records that use lowercase 'twitter' to 'TWITTER'
    op.execute("""
        UPDATE platform_connections 
        SET platform = 'TWITTER' 
        WHERE platform = 'twitter'
    """)
    
    # Note: PostgreSQL doesn't allow removing enum values easily
    # The lowercase 'twitter' value will remain in the enum type but won't be used
    # In a production environment, you would need to:
    # 1. Create a new enum type with correct values
    # 2. Alter all columns to use the new type
    # 3. Drop the old enum type
    
    # For now, we'll just ensure TWITTER exists (it already does from migration 007)
    # and update the Python code to use uppercase values


def downgrade() -> None:
    # Revert any twitter records back to lowercase
    op.execute("""
        UPDATE platform_connections 
        SET platform = 'twitter' 
        WHERE platform = 'TWITTER'
    """)
