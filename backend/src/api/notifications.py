"""Notification API endpoints"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import User, Notification, NotificationTypeEnum
from ..services.notification_service import NotificationService
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# Pydantic schemas
class NotificationResponse(BaseModel):
    """Response model for notification"""
    id: str
    type: str
    title: str
    message: str
    metadata: dict
    is_read: bool
    created_at: str
    
    class Config:
        from_attributes = True


class NotificationPreferencesUpdate(BaseModel):
    """Request model for updating notification preferences"""
    post_success_email: Optional[bool] = None
    post_success_in_app: Optional[bool] = None
    post_failure_email: Optional[bool] = None
    post_failure_in_app: Optional[bool] = None
    schedule_reminder_email: Optional[bool] = None
    schedule_reminder_in_app: Optional[bool] = None
    token_expired_email: Optional[bool] = None
    token_expired_in_app: Optional[bool] = None


class NotificationPreferencesResponse(BaseModel):
    """Response model for notification preferences"""
    post_success_email: bool
    post_success_in_app: bool
    post_failure_email: bool
    post_failure_in_app: bool
    schedule_reminder_email: bool
    schedule_reminder_in_app: bool
    token_expired_email: bool
    token_expired_in_app: bool


class MarkAsReadRequest(BaseModel):
    """Request model for marking notifications as read"""
    notification_ids: Optional[List[str]] = None  # If None, mark all as read


@router.get("", response_model=List[NotificationResponse])
async def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get notifications for the current user.
    
    Args:
        unread_only: Only return unread notifications
        limit: Maximum number of notifications to return (default: 50, max: 100)
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List of notifications
    """
    # Validate limit
    if limit > 100:
        limit = 100
    
    notification_service = NotificationService(db)
    
    notifications = await notification_service.get_user_notifications(
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit
    )
    
    return [
        NotificationResponse(
            id=str(n.id),
            type=n.type.value,
            title=n.title,
            message=n.message,
            metadata=n.metadata,
            is_read=n.is_read,
            created_at=n.created_at.isoformat()
        )
        for n in notifications
    ]


@router.post("/mark-read")
async def mark_notifications_as_read(
    request: MarkAsReadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark notifications as read.
    
    Args:
        request: Request containing notification IDs (or None to mark all as read)
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Success message with count of notifications marked as read
    """
    notification_service = NotificationService(db)
    
    if request.notification_ids is None:
        # Mark all as read
        count = await notification_service.mark_all_as_read(current_user.id)
        return {
            "success": True,
            "message": f"Marked {count} notifications as read"
        }
    else:
        # Mark specific notifications as read
        count = 0
        for notification_id in request.notification_ids:
            try:
                success = await notification_service.mark_as_read(
                    notification_id=UUID(notification_id),
                    user_id=current_user.id
                )
                if success:
                    count += 1
            except ValueError:
                # Invalid UUID, skip
                continue
        
        return {
            "success": True,
            "message": f"Marked {count} notifications as read"
        }


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get notification preferences for the current user.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        User's notification preferences
    """
    prefs = current_user.notification_preferences or {}
    
    # Return preferences with defaults
    return NotificationPreferencesResponse(
        post_success_email=prefs.get("post_success_email", True),
        post_success_in_app=prefs.get("post_success_in_app", True),
        post_failure_email=prefs.get("post_failure_email", True),
        post_failure_in_app=prefs.get("post_failure_in_app", True),
        schedule_reminder_email=prefs.get("schedule_reminder_email", True),
        schedule_reminder_in_app=prefs.get("schedule_reminder_in_app", True),
        token_expired_email=prefs.get("token_expired_email", True),
        token_expired_in_app=prefs.get("token_expired_in_app", True),
    )


@router.patch("/preferences", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    preferences: NotificationPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update notification preferences for the current user.
    
    Args:
        preferences: Notification preferences to update
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Updated notification preferences
    """
    from sqlalchemy import select, update
    
    # Get current preferences
    current_prefs = current_user.notification_preferences or {}
    
    # Update with new values (only update fields that are provided)
    update_data = preferences.model_dump(exclude_unset=True)
    current_prefs.update(update_data)
    
    # Update user in database
    stmt = (
        update(User)
        .where(User.id == current_user.id)
        .values(notification_preferences=current_prefs)
    )
    await db.execute(stmt)
    await db.commit()
    
    # Return updated preferences
    return NotificationPreferencesResponse(
        post_success_email=current_prefs.get("post_success_email", True),
        post_success_in_app=current_prefs.get("post_success_in_app", True),
        post_failure_email=current_prefs.get("post_failure_email", True),
        post_failure_in_app=current_prefs.get("post_failure_in_app", True),
        schedule_reminder_email=current_prefs.get("schedule_reminder_email", True),
        schedule_reminder_in_app=current_prefs.get("schedule_reminder_in_app", True),
        token_expired_email=current_prefs.get("token_expired_email", True),
        token_expired_in_app=current_prefs.get("token_expired_in_app", True),
    )
