"""add notifications

Revision ID: 003
Revises: 002
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create notification type enum
    notification_type_enum = postgresql.ENUM(
        'post_success',
        'post_failure',
        'schedule_reminder',
        'token_expired',
        name='notificationtypeenum',
        create_type=True
    )
    notification_type_enum.create(op.get_bind(), checkfirst=True)
    
    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.Enum(
            'post_success',
            'post_failure',
            'schedule_reminder',
            'token_expired',
            name='notificationtypeenum'
        ), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for notifications
    op.create_index('idx_notification_user_created', 'notifications', ['user_id', 'created_at'])
    op.create_index('idx_notification_user_unread', 'notifications', ['user_id', 'is_read'])
    op.create_index(op.f('ix_notifications_type'), 'notifications', ['type'])
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'])
    
    # Create notification_batches table
    op.create_table(
        'notification_batches',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('notification_type', sa.Enum(
            'post_success',
            'post_failure',
            'schedule_reminder',
            'token_expired',
            name='notificationtypeenum'
        ), nullable=False),
        sa.Column('batch_key', sa.String(length=255), nullable=False),
        sa.Column('notification_ids', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for notification_batches
    op.create_index('idx_batch_user_key', 'notification_batches', ['user_id', 'batch_key'], unique=True)
    op.create_index(op.f('ix_notification_batches_user_id'), 'notification_batches', ['user_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_notification_batches_user_id'), table_name='notification_batches')
    op.drop_index('idx_batch_user_key', table_name='notification_batches')
    
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_type'), table_name='notifications')
    op.drop_index('idx_notification_user_unread', table_name='notifications')
    op.drop_index('idx_notification_user_created', table_name='notifications')
    
    # Drop tables
    op.drop_table('notification_batches')
    op.drop_table('notifications')
    
    # Drop enum
    sa.Enum(name='notificationtypeenum').drop(op.get_bind(), checkfirst=True)
