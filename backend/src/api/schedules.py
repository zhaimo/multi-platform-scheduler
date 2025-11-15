"""Schedule management API endpoints"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.utils.auth import get_current_user
from src.models.database_models import User, Schedule, PlatformEnum
from src.services.scheduler_service import SchedulerService
from src.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


# Request/Response Models
class ScheduleCreateRequest(BaseModel):
    """Request model for creating a schedule"""
    video_id: uuid.UUID = Field(..., description="ID of the video to schedule")
    platforms: List[str] = Field(..., description="List of platforms to post to", min_items=1)
    post_config: Dict[str, Dict[str, Any]] = Field(
        ...,
        description="Platform-specific configurations",
        example={
            "tiktok": {"caption": "Check this out!", "hashtags": ["viral", "trending"]},
            "youtube": {"caption": "New video!", "hashtags": ["shorts"]}
        }
    )
    scheduled_at: datetime = Field(..., description="When to post the video (UTC)")
    is_recurring: bool = Field(default=False, description="Whether this is a recurring schedule")
    recurrence_pattern: Optional[str] = Field(
        None,
        description="Cron-like pattern for recurring schedules (e.g., '0 9 * * 1' for every Monday at 9am)"
    )
    
    @validator("platforms")
    def validate_platforms(cls, v):
        """Validate platform names"""
        valid_platforms = [p.value for p in PlatformEnum]
        for platform in v:
            if platform not in valid_platforms:
                raise ValueError(f"Invalid platform: {platform}. Valid platforms: {valid_platforms}")
        return v
    
    @validator("recurrence_pattern")
    def validate_recurrence(cls, v, values):
        """Validate recurrence pattern is provided if is_recurring is True"""
        if values.get("is_recurring") and not v:
            raise ValueError("recurrence_pattern is required when is_recurring is True")
        return v


class ScheduleUpdateRequest(BaseModel):
    """Request model for updating a schedule"""
    scheduled_at: Optional[datetime] = Field(None, description="New scheduled time (UTC)")
    platforms: Optional[List[str]] = Field(None, description="New list of platforms", min_items=1)
    post_config: Optional[Dict[str, Dict[str, Any]]] = Field(
        None,
        description="New platform-specific configurations"
    )
    recurrence_pattern: Optional[str] = Field(
        None,
        description="New cron-like pattern for recurring schedules"
    )
    
    @validator("platforms")
    def validate_platforms(cls, v):
        """Validate platform names"""
        if v is not None:
            valid_platforms = [p.value for p in PlatformEnum]
            for platform in v:
                if platform not in valid_platforms:
                    raise ValueError(f"Invalid platform: {platform}. Valid platforms: {valid_platforms}")
        return v


class ScheduleResponse(BaseModel):
    """Response model for schedule"""
    id: uuid.UUID
    user_id: uuid.UUID
    video_id: uuid.UUID
    platforms: List[str]
    post_config: Dict[str, Dict[str, Any]]
    scheduled_at: datetime
    is_recurring: bool
    recurrence_pattern: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_schedule(cls, schedule: Schedule) -> "ScheduleResponse":
        """Convert Schedule model to response"""
        return cls(
            id=schedule.id,
            user_id=schedule.user_id,
            video_id=schedule.video_id,
            platforms=[p.value for p in schedule.platforms],
            post_config=schedule.post_config,
            scheduled_at=schedule.scheduled_at,
            is_recurring=schedule.is_recurring,
            recurrence_pattern=schedule.recurrence_pattern,
            is_active=schedule.is_active,
            created_at=schedule.created_at,
            updated_at=schedule.updated_at
        )


class ScheduleListResponse(BaseModel):
    """Response model for list of schedules"""
    schedules: List[ScheduleResponse]
    total: int


# Endpoints
@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    request: ScheduleCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new scheduled post.
    
    The scheduled time must be at least 5 minutes in the future.
    For recurring schedules, provide a cron-like pattern.
    
    **Cron Pattern Examples:**
    - `0 9 * * *` - Every day at 9:00 AM
    - `0 9 * * 1` - Every Monday at 9:00 AM
    - `0 */6 * * *` - Every 6 hours
    - `0 9,18 * * *` - Every day at 9:00 AM and 6:00 PM
    """
    try:
        scheduler_service = SchedulerService(settings)
        
        schedule = await scheduler_service.schedule_post(
            db=db,
            user_id=current_user.id,
            video_id=request.video_id,
            platforms=request.platforms,
            post_config=request.post_config,
            scheduled_at=request.scheduled_at,
            is_recurring=request.is_recurring,
            recurrence_pattern=request.recurrence_pattern
        )
        
        logger.info(f"User {current_user.id} created schedule {schedule.id}")
        
        return ScheduleResponse.from_schedule(schedule)
    
    except ValueError as e:
        logger.warning(f"Validation error creating schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating schedule: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create schedule"
        )


@router.get("", response_model=ScheduleListResponse)
async def list_schedules(
    limit: int = 50,
    include_inactive: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List user's scheduled posts.
    
    Returns schedules ordered by scheduled time (earliest first).
    By default, only active schedules are returned.
    """
    try:
        scheduler_service = SchedulerService(settings)
        
        schedules = await scheduler_service.get_upcoming_schedules(
            db=db,
            user_id=current_user.id,
            limit=limit,
            include_inactive=include_inactive
        )
        
        schedule_responses = [ScheduleResponse.from_schedule(s) for s in schedules]
        
        return ScheduleListResponse(
            schedules=schedule_responses,
            total=len(schedule_responses)
        )
    
    except Exception as e:
        logger.error(f"Error listing schedules: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list schedules"
        )


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific schedule.
    """
    try:
        scheduler_service = SchedulerService(settings)
        
        schedule = await scheduler_service.get_schedule(
            db=db,
            schedule_id=schedule_id,
            user_id=current_user.id
        )
        
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule not found: {schedule_id}"
            )
        
        return ScheduleResponse.from_schedule(schedule)
    
    except ValueError as e:
        logger.warning(f"Authorization error getting schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting schedule: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get schedule"
        )


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: uuid.UUID,
    request: ScheduleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a scheduled post.
    
    You can update the scheduled time, platforms, post configuration, or recurrence pattern.
    The scheduled time must be at least 5 minutes in the future.
    """
    try:
        scheduler_service = SchedulerService(settings)
        
        schedule = await scheduler_service.update_schedule(
            db=db,
            schedule_id=schedule_id,
            user_id=current_user.id,
            scheduled_at=request.scheduled_at,
            platforms=request.platforms,
            post_config=request.post_config,
            recurrence_pattern=request.recurrence_pattern
        )
        
        logger.info(f"User {current_user.id} updated schedule {schedule_id}")
        
        return ScheduleResponse.from_schedule(schedule)
    
    except ValueError as e:
        logger.warning(f"Validation error updating schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating schedule: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update schedule"
        )


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_schedule(
    schedule_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a scheduled post.
    
    This marks the schedule as inactive and prevents it from being executed.
    """
    try:
        scheduler_service = SchedulerService(settings)
        
        success = await scheduler_service.cancel_schedule(
            db=db,
            schedule_id=schedule_id,
            user_id=current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule not found: {schedule_id}"
            )
        
        logger.info(f"User {current_user.id} cancelled schedule {schedule_id}")
        
        return None
    
    except ValueError as e:
        logger.warning(f"Authorization error cancelling schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling schedule: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel schedule"
        )
