"""Notification service for email and in-app notifications"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ..models.notification_models import (
    Notification,
    NotificationBatch,
    NotificationTypeEnum,
    NotificationChannelEnum,
)
from ..models.database_models import User
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class NotificationService:
    """Service for managing notifications"""
    
    # Batching window in minutes
    BATCH_WINDOW_MINUTES = 5
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_notification(
        self,
        user_id: UUID,
        notification_type: NotificationTypeEnum,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        """
        Create an in-app notification
        
        Args:
            user_id: User ID to notify
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            metadata: Additional context data
        
        Returns:
            Created notification
        """
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            context_data=metadata or {},
        )
        
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        
        logger.info(f"Created notification {notification.id} for user {user_id}")
        return notification
    
    async def get_user_notifications(
        self,
        user_id: UUID,
        unread_only: bool = False,
        limit: int = 50,
    ) -> List[Notification]:
        """
        Get notifications for a user
        
        Args:
            user_id: User ID
            unread_only: Only return unread notifications
            limit: Maximum number of notifications to return
        
        Returns:
            List of notifications
        """
        query = select(Notification).where(Notification.user_id == user_id)
        
        if unread_only:
            query = query.where(Notification.is_read == False)
        
        query = query.order_by(Notification.created_at.desc()).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def mark_as_read(self, notification_id: UUID, user_id: UUID) -> bool:
        """
        Mark a notification as read
        
        Args:
            notification_id: Notification ID
            user_id: User ID (for authorization)
        
        Returns:
            True if marked as read, False if not found
        """
        query = select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        result = await self.db.execute(query)
        notification = result.scalar_one_or_none()
        
        if not notification:
            return False
        
        notification.is_read = True
        await self.db.commit()
        
        logger.info(f"Marked notification {notification_id} as read")
        return True
    
    async def mark_all_as_read(self, user_id: UUID) -> int:
        """
        Mark all notifications as read for a user
        
        Args:
            user_id: User ID
        
        Returns:
            Number of notifications marked as read
        """
        query = select(Notification).where(
            and_(
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
        )
        result = await self.db.execute(query)
        notifications = result.scalars().all()
        
        count = 0
        for notification in notifications:
            notification.is_read = True
            count += 1
        
        await self.db.commit()
        
        logger.info(f"Marked {count} notifications as read for user {user_id}")
        return count
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> bool:
        """
        Send an email notification
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Plain text email body
            html_body: Optional HTML email body
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not settings.smtp_user or not settings.smtp_password:
            logger.warning("SMTP credentials not configured, skipping email send")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
            msg["To"] = to_email
            
            # Add plain text part
            text_part = MIMEText(body, "plain")
            msg.attach(text_part)
            
            # Add HTML part if provided
            if html_body:
                html_part = MIMEText(html_body, "html")
                msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Sent email to {to_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    async def should_send_notification(
        self,
        user_id: UUID,
        notification_type: NotificationTypeEnum,
        channel: NotificationChannelEnum,
    ) -> bool:
        """
        Check if a notification should be sent based on user preferences
        
        Args:
            user_id: User ID
            notification_type: Type of notification
            channel: Notification channel (email or in_app)
        
        Returns:
            True if notification should be sent
        """
        # Get user preferences
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        # Check preferences
        prefs = user.notification_preferences or {}
        
        # Default to enabled if not specified
        type_key = f"{notification_type.value}_{channel.value}"
        return prefs.get(type_key, True)
    
    async def get_or_create_batch(
        self,
        user_id: UUID,
        notification_type: NotificationTypeEnum,
    ) -> NotificationBatch:
        """
        Get or create a notification batch for the current batching window
        
        Args:
            user_id: User ID
            notification_type: Type of notification
        
        Returns:
            Notification batch
        """
        # Create batch key based on current time window
        now = datetime.utcnow()
        window_start = now.replace(second=0, microsecond=0)
        window_start = window_start - timedelta(
            minutes=window_start.minute % self.BATCH_WINDOW_MINUTES
        )
        batch_key = f"{notification_type.value}_{window_start.isoformat()}"
        
        # Try to get existing batch
        query = select(NotificationBatch).where(
            and_(
                NotificationBatch.user_id == user_id,
                NotificationBatch.batch_key == batch_key,
            )
        )
        result = await self.db.execute(query)
        batch = result.scalar_one_or_none()
        
        if batch:
            return batch
        
        # Create new batch
        batch = NotificationBatch(
            user_id=user_id,
            notification_type=notification_type,
            batch_key=batch_key,
            notification_ids=[],
        )
        
        self.db.add(batch)
        await self.db.commit()
        await self.db.refresh(batch)
        
        logger.info(f"Created notification batch {batch.id} for user {user_id}")
        return batch
    
    async def add_to_batch(
        self,
        batch: NotificationBatch,
        notification_id: UUID,
    ) -> None:
        """
        Add a notification to a batch
        
        Args:
            batch: Notification batch
            notification_id: Notification ID to add
        """
        notification_ids = batch.notification_ids or []
        notification_ids.append(str(notification_id))
        batch.notification_ids = notification_ids
        
        await self.db.commit()
        logger.info(f"Added notification {notification_id} to batch {batch.id}")
    
    async def send_batched_notifications(
        self,
        user_id: UUID,
        notification_type: NotificationTypeEnum,
    ) -> bool:
        """
        Send batched notifications via email
        
        Args:
            user_id: User ID
            notification_type: Type of notification
        
        Returns:
            True if sent successfully
        """
        # Get user
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.error(f"User {user_id} not found")
            return False
        
        # Check if email notifications are enabled
        if not await self.should_send_notification(
            user_id, notification_type, NotificationChannelEnum.EMAIL
        ):
            logger.info(f"Email notifications disabled for user {user_id}")
            return False
        
        # Get unsent batches older than batching window
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.BATCH_WINDOW_MINUTES)
        query = select(NotificationBatch).where(
            and_(
                NotificationBatch.user_id == user_id,
                NotificationBatch.notification_type == notification_type,
                NotificationBatch.sent_at.is_(None),
                NotificationBatch.created_at < cutoff_time,
            )
        )
        result = await self.db.execute(query)
        batches = result.scalars().all()
        
        if not batches:
            return True
        
        # Collect all notifications from batches
        all_notification_ids = []
        for batch in batches:
            all_notification_ids.extend(batch.notification_ids or [])
        
        if not all_notification_ids:
            return True
        
        # Get notification details
        query = select(Notification).where(
            Notification.id.in_([UUID(nid) for nid in all_notification_ids])
        )
        result = await self.db.execute(query)
        notifications = result.scalars().all()
        
        # Build email content
        subject = self._build_batch_subject(notification_type, len(notifications))
        body = self._build_batch_body(notifications)
        html_body = self._build_batch_html_body(notifications)
        
        # Send email
        success = await self.send_email(user.email, subject, body, html_body)
        
        if success:
            # Mark batches as sent
            for batch in batches:
                batch.sent_at = datetime.utcnow()
            await self.db.commit()
            
            logger.info(f"Sent batched notifications to {user.email}")
        
        return success
    
    def _build_batch_subject(
        self,
        notification_type: NotificationTypeEnum,
        count: int,
    ) -> str:
        """Build email subject for batched notifications"""
        if count == 1:
            if notification_type == NotificationTypeEnum.POST_SUCCESS:
                return "Your video was posted successfully"
            elif notification_type == NotificationTypeEnum.POST_FAILURE:
                return "Your video post failed"
            else:
                return "Notification from Video Scheduler"
        else:
            if notification_type == NotificationTypeEnum.POST_SUCCESS:
                return f"{count} videos were posted successfully"
            elif notification_type == NotificationTypeEnum.POST_FAILURE:
                return f"{count} video posts failed"
            else:
                return f"{count} notifications from Video Scheduler"
    
    def _build_batch_body(self, notifications: List[Notification]) -> str:
        """Build plain text email body for batched notifications"""
        lines = ["Here's a summary of your recent activity:\n"]
        
        for notification in notifications:
            lines.append(f"• {notification.title}")
            lines.append(f"  {notification.message}\n")
        
        lines.append("\nLog in to your dashboard to view more details.")
        return "\n".join(lines)
    
    def _build_batch_html_body(self, notifications: List[Notification]) -> str:
        """Build HTML email body for batched notifications"""
        items = []
        for notification in notifications:
            items.append(f"""
                <div style="margin-bottom: 20px; padding: 15px; background-color: #f5f5f5; border-radius: 5px;">
                    <h3 style="margin: 0 0 10px 0; color: #333;">{notification.title}</h3>
                    <p style="margin: 0; color: #666;">{notification.message}</p>
                </div>
            """)
        
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #333;">Activity Summary</h2>
                <p style="color: #666;">Here's a summary of your recent activity:</p>
                {''.join(items)}
                <p style="margin-top: 30px; color: #666;">
                    <a href="#" style="color: #007bff; text-decoration: none;">Log in to your dashboard</a> 
                    to view more details.
                </p>
            </body>
        </html>
        """
        return html


async def get_notification_service(db: AsyncSession) -> NotificationService:
    """Dependency injection for notification service"""
    return NotificationService(db)
