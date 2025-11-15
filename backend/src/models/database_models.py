import enum
from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
    Index,
    Enum as SQLEnum,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship, declarative_base
from cryptography.fernet import Fernet
import os

Base = declarative_base()


# Enums
class PlatformEnum(str, enum.Enum):
    TIKTOK = "TIKTOK"
    YOUTUBE = "YOUTUBE"
    TWITTER = "TWITTER"
    INSTAGRAM = "INSTAGRAM"
    FACEBOOK = "FACEBOOK"


class PostStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    POSTED = "posted"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Encryption utility
class EncryptionMixin:
    """Mixin for encrypting/decrypting sensitive fields"""
    
    @staticmethod
    def encrypt_value(value: str) -> str:
        """Encrypt a string value using the encryption service"""
        if not value:
            return value
        from src.utils.encryption import get_encryption_service
        return get_encryption_service().encrypt(value)
    
    @staticmethod
    def decrypt_value(encrypted_value: str) -> str:
        """Decrypt an encrypted string value using the encryption service"""
        if not encrypted_value:
            return encrypted_value
        from src.utils.encryption import get_encryption_service
        return get_encryption_service().decrypt(encrypted_value)


# Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    notification_preferences = Column(JSON, default=dict, nullable=False)
    
    # Relationships
    videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")
    platform_auths = relationship("PlatformAuth", back_populates="user", cascade="all, delete-orphan")
    platform_connections = relationship("PlatformConnection", back_populates="user", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="user", cascade="all, delete-orphan")
    multi_posts = relationship("MultiPost", back_populates="user", cascade="all, delete-orphan")
    schedules = relationship("Schedule", back_populates="user", cascade="all, delete-orphan")
    templates = relationship("PostTemplate", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class Video(Base):
    __tablename__ = "videos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_url = Column(String(512), nullable=False)
    thumbnail_url = Column(String(512), nullable=True)
    duration = Column(Integer, nullable=False)  # seconds
    format = Column(String(50), nullable=False)
    resolution = Column(String(50), nullable=False)
    file_size = Column(Integer, nullable=False)  # bytes
    tags = Column(ARRAY(String), default=list, nullable=False)
    category = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="videos")
    posts = relationship("Post", back_populates="video", cascade="all, delete-orphan")
    analytics = relationship("VideoAnalytics", back_populates="video", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_video_user_created", "user_id", "created_at"),
        Index("idx_video_tags", "tags", postgresql_using="gin"),
    )
    
    def __repr__(self):
        return f"<Video(id={self.id}, title={self.title})>"


class PlatformAuth(Base, EncryptionMixin):
    __tablename__ = "platform_auths"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(SQLEnum(PlatformEnum), nullable=False, index=True)
    access_token = Column(Text, nullable=False)  # Encrypted
    refresh_token = Column(Text, nullable=True)  # Encrypted
    token_expires_at = Column(DateTime, nullable=False)
    platform_user_id = Column(String(255), nullable=False)
    platform_username = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="platform_auths")
    
    # Indexes
    __table_args__ = (
        Index("idx_platform_auth_user_platform", "user_id", "platform", unique=True),
    )
    
    def set_access_token(self, token: str):
        """Encrypt and set access token"""
        self.access_token = self.encrypt_value(token)
    
    def get_access_token(self) -> str:
        """Decrypt and return access token"""
        return self.decrypt_value(self.access_token)
    
    def set_refresh_token(self, token: str):
        """Encrypt and set refresh token"""
        if token:
            self.refresh_token = self.encrypt_value(token)
    
    def get_refresh_token(self) -> Optional[str]:
        """Decrypt and return refresh token"""
        if self.refresh_token:
            return self.decrypt_value(self.refresh_token)
        return None
    
    def __repr__(self):
        return f"<PlatformAuth(id={self.id}, platform={self.platform}, user_id={self.user_id})>"


class Post(Base):
    __tablename__ = "posts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    multi_post_id = Column(UUID(as_uuid=True), ForeignKey("multi_posts.id", ondelete="SET NULL"), nullable=True)
    platform = Column(SQLEnum(PlatformEnum), nullable=False, index=True)
    status = Column(SQLEnum(PostStatusEnum), default=PostStatusEnum.PENDING, nullable=False, index=True)
    platform_post_id = Column(String(255), nullable=True)
    platform_url = Column(String(512), nullable=True)
    caption = Column(Text, nullable=False)
    hashtags = Column(ARRAY(String), default=list, nullable=False)
    scheduled_at = Column(DateTime, nullable=True)
    posted_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="posts")
    video = relationship("Video", back_populates="posts")
    multi_post = relationship("MultiPost", back_populates="posts")
    
    # Indexes
    __table_args__ = (
        Index("idx_post_user_status", "user_id", "status"),
        Index("idx_post_video_platform", "video_id", "platform"),
        Index("idx_post_scheduled", "scheduled_at"),
    )
    
    def __repr__(self):
        return f"<Post(id={self.id}, platform={self.platform}, status={self.status})>"


class MultiPost(Base):
    __tablename__ = "multi_posts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="multi_posts")
    posts = relationship("Post", back_populates="multi_post", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<MultiPost(id={self.id}, video_id={self.video_id})>"


class Schedule(Base):
    __tablename__ = "schedules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    platforms = Column(ARRAY(SQLEnum(PlatformEnum)), nullable=False)
    post_config = Column(JSON, nullable=False)  # Platform-specific captions, hashtags
    scheduled_at = Column(DateTime, nullable=False, index=True)
    is_recurring = Column(Boolean, default=False, nullable=False)
    recurrence_pattern = Column(String(255), nullable=True)  # cron-like pattern
    caption_rotation_index = Column(Integer, default=0, nullable=False)  # Track current caption variation
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="schedules")
    
    # Indexes
    __table_args__ = (
        Index("idx_schedule_active_time", "is_active", "scheduled_at"),
    )
    
    def __repr__(self):
        return f"<Schedule(id={self.id}, scheduled_at={self.scheduled_at})>"


class PostTemplate(Base):
    __tablename__ = "post_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    platform_configs = Column(JSON, nullable=False)  # Platform -> {caption, hashtags}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="templates")
    
    def __repr__(self):
        return f"<PostTemplate(id={self.id}, name={self.name})>"


class VideoAnalytics(Base):
    __tablename__ = "video_analytics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(SQLEnum(PlatformEnum), nullable=False, index=True)
    platform_post_id = Column(String(255), nullable=False)
    views = Column(Integer, default=0, nullable=False)
    likes = Column(Integer, default=0, nullable=False)
    comments = Column(Integer, default=0, nullable=False)
    shares = Column(Integer, default=0, nullable=False)
    synced_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    video = relationship("Video", back_populates="analytics")
    
    # Indexes
    __table_args__ = (
        Index("idx_analytics_video_platform", "video_id", "platform"),
    )
    
    def __repr__(self):
        return f"<VideoAnalytics(id={self.id}, platform={self.platform}, views={self.views})>"


class PlatformConnection(Base):
    """Platform OAuth connection for users"""
    __tablename__ = "platform_connections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(SQLEnum(PlatformEnum), nullable=False, index=True)
    platform_user_id = Column(String(255))
    platform_username = Column(String(255))
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime)
    scopes = Column(JSON, default=list)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="platform_connections")
    
    # Unique constraint
    __table_args__ = (
        Index("idx_platform_connection_user_platform", "user_id", "platform", unique=True),
    )
    
    def __repr__(self):
        return f"<PlatformConnection(id={self.id}, user_id={self.user_id}, platform={self.platform})>"
