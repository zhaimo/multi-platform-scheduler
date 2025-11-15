"""Notification-related database models"""

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
    Index,
    Enum as SQLEnum,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database_models import Base


class NotificationTypeEnum(str, enum.Enum):
    """Types of notifications"""
    POST_SUCCESS = "post_success"
    POST_FAILURE = "post_failure"
    SCHEDULE_REMINDER = "schedule_reminder"
    TOKEN_EXPIRED = "token_expired"


class NotificationChannelEnum(str, enum.Enum):
    """Notification delivery channels"""
    EMAIL = "email"
    IN_APP = "in_app"


class Notification(Base):
    """In-app notification storage"""
    __tablename__ = "notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(SQLEnum(NotificationTypeEnum), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    context_data = Column(JSON, default=dict, nullable=False)  # Additional context (post_id, video_id, etc.)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_notification_user_created", "user_id", "created_at"),
        Index("idx_notification_user_unread", "user_id", "is_read"),
    )
    
    def __repr__(self):
        return f"<Notification(id={self.id}, type={self.type}, user_id={self.user_id})>"


class NotificationBatch(Base):
    """Track notification batches to prevent duplicate sends within batching window"""
    __tablename__ = "notification_batches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    notification_type = Column(SQLEnum(NotificationTypeEnum), nullable=False)
    batch_key = Column(String(255), nullable=False)  # Unique key for this batch window
    notification_ids = Column(JSON, default=list, nullable=False)  # List of notification IDs in this batch
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_batch_user_key", "user_id", "batch_key", unique=True),
    )
    
    def __repr__(self):
        return f"<NotificationBatch(id={self.id}, user_id={self.user_id}, type={self.notification_type})>"
