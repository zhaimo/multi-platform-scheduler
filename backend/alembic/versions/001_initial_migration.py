"""Initial migration with all tables

Revision ID: 001
Revises: 
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE platformenum AS ENUM ('tiktok', 'youtube', 'instagram', 'facebook')")
    op.execute("CREATE TYPE poststatusenum AS ENUM ('pending', 'processing', 'posted', 'failed', 'cancelled')")
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('notification_preferences', postgresql.JSON(), nullable=False, server_default='{}'),
    )
    op.create_index('ix_users_email', 'users', ['email'])
    
    # Create videos table
    op.create_table(
        'videos',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('file_url', sa.String(512), nullable=False),
        sa.Column('thumbnail_url', sa.String(512), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=False),
        sa.Column('format', sa.String(50), nullable=False),
        sa.Column('resolution', sa.String(50), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_videos_user_id', 'videos', ['user_id'])
    op.create_index('idx_video_user_created', 'videos', ['user_id', 'created_at'])
    op.create_index('idx_video_tags', 'videos', ['tags'], postgresql_using='gin')
    
    # Create platform_auths table
    op.create_table(
        'platform_auths',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('platform', sa.Enum('tiktok', 'youtube', 'instagram', 'facebook', name='platformenum'), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(), nullable=False),
        sa.Column('platform_user_id', sa.String(255), nullable=False),
        sa.Column('platform_username', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_platform_auths_user_id', 'platform_auths', ['user_id'])
    op.create_index('ix_platform_auths_platform', 'platform_auths', ['platform'])
    op.create_index('idx_platform_auth_user_platform', 'platform_auths', ['user_id', 'platform'], unique=True)
    
    # Create multi_posts table
    op.create_table(
        'multi_posts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('video_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_multi_posts_user_id', 'multi_posts', ['user_id'])
    op.create_index('ix_multi_posts_video_id', 'multi_posts', ['video_id'])
    
    # Create posts table
    op.create_table(
        'posts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('video_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('multi_post_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('platform', sa.Enum('tiktok', 'youtube', 'instagram', 'facebook', name='platformenum'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'processing', 'posted', 'failed', 'cancelled', name='poststatusenum'), nullable=False, server_default='pending'),
        sa.Column('platform_post_id', sa.String(255), nullable=True),
        sa.Column('platform_url', sa.String(512), nullable=True),
        sa.Column('caption', sa.Text(), nullable=False),
        sa.Column('hashtags', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('scheduled_at', sa.DateTime(), nullable=True),
        sa.Column('posted_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['multi_post_id'], ['multi_posts.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_posts_user_id', 'posts', ['user_id'])
    op.create_index('ix_posts_video_id', 'posts', ['video_id'])
    op.create_index('ix_posts_platform', 'posts', ['platform'])
    op.create_index('ix_posts_status', 'posts', ['status'])
    op.create_index('idx_post_user_status', 'posts', ['user_id', 'status'])
    op.create_index('idx_post_video_platform', 'posts', ['video_id', 'platform'])
    op.create_index('idx_post_scheduled', 'posts', ['scheduled_at'])
    
    # Create schedules table
    op.create_table(
        'schedules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('video_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('platforms', postgresql.ARRAY(sa.Enum('tiktok', 'youtube', 'instagram', 'facebook', name='platformenum')), nullable=False),
        sa.Column('post_config', postgresql.JSON(), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False),
        sa.Column('is_recurring', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('recurrence_pattern', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_schedules_user_id', 'schedules', ['user_id'])
    op.create_index('ix_schedules_video_id', 'schedules', ['video_id'])
    op.create_index('ix_schedules_scheduled_at', 'schedules', ['scheduled_at'])
    op.create_index('ix_schedules_is_active', 'schedules', ['is_active'])
    op.create_index('idx_schedule_active_time', 'schedules', ['is_active', 'scheduled_at'])
    
    # Create post_templates table
    op.create_table(
        'post_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('platform_configs', postgresql.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_post_templates_user_id', 'post_templates', ['user_id'])
    
    # Create video_analytics table
    op.create_table(
        'video_analytics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('video_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('platform', sa.Enum('tiktok', 'youtube', 'instagram', 'facebook', name='platformenum'), nullable=False),
        sa.Column('platform_post_id', sa.String(255), nullable=False),
        sa.Column('views', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('likes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('comments', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('shares', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('synced_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_video_analytics_video_id', 'video_analytics', ['video_id'])
    op.create_index('ix_video_analytics_platform', 'video_analytics', ['platform'])
    op.create_index('idx_analytics_video_platform', 'video_analytics', ['video_id', 'platform'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('video_analytics')
    op.drop_table('post_templates')
    op.drop_table('schedules')
    op.drop_table('posts')
    op.drop_table('multi_posts')
    op.drop_table('platform_auths')
    op.drop_table('videos')
    op.drop_table('users')
    
    # Drop enum types
    op.execute('DROP TYPE poststatusenum')
    op.execute('DROP TYPE platformenum')
