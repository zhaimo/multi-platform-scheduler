"""Scheduler service for managing scheduled and recurring posts"""

import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
from croniter import croniter

from src.models.database_models import (
    Schedule,
    Video,
    PlatformAuth,
    PlatformEnum,
    User
)
from src.config import Settings

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing scheduled and recurring posts"""
    
    def __init__(self, settings: Settings):
        """Initialize scheduler service
        
        Args:
            settings: Application settings
        """
        self.settings = settings
    
    async def schedule_post(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        video_id: uuid.UUID,
        platforms: List[str],
        post_config: Dict[str, Dict[str, Any]],
        scheduled_at: datetime,
        is_recurring: bool = False,
        recurrence_pattern: Optional[str] = None
    ) -> Schedule:
        """Create a scheduled post
        
        Args:
            db: Database session
            user_id: ID of the user creating the schedule
            video_id: ID of the video to post
            platforms: List of platform names to post to
            post_config: Dictionary mapping platform names to their configs
                Example: {
                    "tiktok": {"caption": "...", "hashtags": [...]},
                    "youtube": {"caption": "...", "hashtags": [...]}
                }
            scheduled_at: When to post the video
            is_recurring: Whether this is a recurring schedule
            recurrence_pattern: Cron-like pattern for recurring schedules
            
        Returns:
            Created Schedule object
            
        Raises:
            ValueError: If validation fails
        """
        # Validate scheduled time is at least 5 minutes in the future
        min_schedule_time = datetime.utcnow() + timedelta(minutes=5)
        if scheduled_at < min_schedule_time:
            raise ValueError(
                f"Scheduled time must be at least 5 minutes in the future. "
                f"Minimum allowed time: {min_schedule_time.isoformat()}"
            )
        
        # Validate video exists and belongs to user
        video = await self._get_video(db, video_id, user_id)
        if not video:
            raise ValueError(f"Video not found or does not belong to user: {video_id}")
        
        # Validate platforms
        if not platforms:
            raise ValueError("At least one platform must be specified")
        
        # Convert platform names to enums and validate
        platform_enums = []
        for platform_name in platforms:
            try:
                # Convert to uppercase to match enum values
                platform_enum = PlatformEnum(platform_name.upper())
                platform_enums.append(platform_enum)
            except ValueError:
                raise ValueError(f"Invalid platform: {platform_name}")
        
        # Validate user has authenticated with all platforms
        await self._validate_platform_auth(db, user_id, platforms)
        
        # Validate recurrence pattern if recurring
        if is_recurring:
            if not recurrence_pattern:
                raise ValueError("Recurrence pattern is required for recurring schedules")
            
            self._validate_recurrence_pattern(recurrence_pattern)
        
        # Create Schedule record
        schedule = Schedule(
            id=uuid.uuid4(),
            user_id=user_id,
            video_id=video_id,
            platforms=platform_enums,
            post_config=post_config,
            scheduled_at=scheduled_at,
            is_recurring=is_recurring,
            recurrence_pattern=recurrence_pattern,
            is_active=True
        )
        
        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)
        
        logger.info(
            f"Created schedule {schedule.id} for video {video_id} "
            f"at {scheduled_at.isoformat()}, recurring={is_recurring}"
        )
        
        return schedule
    
    async def create_recurring_schedule(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        video_id: uuid.UUID,
        platforms: List[str],
        post_config: Dict[str, Dict[str, Any]],
        recurrence_pattern: str,
        start_time: Optional[datetime] = None
    ) -> Schedule:
        """Create a recurring schedule
        
        Args:
            db: Database session
            user_id: ID of the user creating the schedule
            video_id: ID of the video to post
            platforms: List of platform names to post to
            post_config: Dictionary mapping platform names to their configs
            recurrence_pattern: Cron-like pattern (e.g., "0 9 * * 1" for every Monday at 9am)
            start_time: Optional start time (defaults to next occurrence from now)
            
        Returns:
            Created Schedule object
            
        Raises:
            ValueError: If validation fails
        """
        # Validate recurrence pattern
        self._validate_recurrence_pattern(recurrence_pattern)
        
        # Calculate first scheduled time
        if start_time is None:
            # Use next occurrence from now
            cron = croniter(recurrence_pattern, datetime.utcnow())
            scheduled_at = cron.get_next(datetime)
        else:
            scheduled_at = start_time
        
        # Create recurring schedule
        return await self.schedule_post(
            db=db,
            user_id=user_id,
            video_id=video_id,
            platforms=platforms,
            post_config=post_config,
            scheduled_at=scheduled_at,
            is_recurring=True,
            recurrence_pattern=recurrence_pattern
        )
    
    async def cancel_schedule(
        self,
        db: AsyncSession,
        schedule_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """Cancel a scheduled post
        
        Args:
            db: Database session
            schedule_id: Schedule ID
            user_id: User ID (for authorization)
            
        Returns:
            True if cancelled successfully, False if not found
            
        Raises:
            ValueError: If schedule doesn't belong to user
        """
        # Get schedule
        query = select(Schedule).where(Schedule.id == schedule_id)
        result = await db.execute(query)
        schedule = result.scalar_one_or_none()
        
        if not schedule:
            return False
        
        # Verify ownership
        if schedule.user_id != user_id:
            raise ValueError("Schedule does not belong to user")
        
        # Mark as inactive
        schedule.is_active = False
        await db.commit()
        
        logger.info(f"Cancelled schedule {schedule_id}")
        
        return True
    
    async def update_schedule(
        self,
        db: AsyncSession,
        schedule_id: uuid.UUID,
        user_id: uuid.UUID,
        scheduled_at: Optional[datetime] = None,
        platforms: Optional[List[str]] = None,
        post_config: Optional[Dict[str, Dict[str, Any]]] = None,
        recurrence_pattern: Optional[str] = None
    ) -> Schedule:
        """Update a scheduled post
        
        Args:
            db: Database session
            schedule_id: Schedule ID
            user_id: User ID (for authorization)
            scheduled_at: New scheduled time
            platforms: New list of platforms
            post_config: New post configuration
            recurrence_pattern: New recurrence pattern
            
        Returns:
            Updated Schedule object
            
        Raises:
            ValueError: If validation fails or schedule not found
        """
        # Get schedule
        query = select(Schedule).where(Schedule.id == schedule_id)
        result = await db.execute(query)
        schedule = result.scalar_one_or_none()
        
        if not schedule:
            raise ValueError(f"Schedule not found: {schedule_id}")
        
        # Verify ownership
        if schedule.user_id != user_id:
            raise ValueError("Schedule does not belong to user")
        
        # Verify schedule is still active
        if not schedule.is_active:
            raise ValueError("Cannot update cancelled schedule")
        
        # Update scheduled time if provided
        if scheduled_at is not None:
            # Validate scheduled time is at least 5 minutes in the future
            min_schedule_time = datetime.utcnow() + timedelta(minutes=5)
            if scheduled_at < min_schedule_time:
                raise ValueError(
                    f"Scheduled time must be at least 5 minutes in the future. "
                    f"Minimum allowed time: {min_schedule_time.isoformat()}"
                )
            schedule.scheduled_at = scheduled_at
        
        # Update platforms if provided
        if platforms is not None:
            if not platforms:
                raise ValueError("At least one platform must be specified")
            
            # Convert to enums and validate
            platform_enums = []
            for platform_name in platforms:
                try:
                    # Convert to uppercase to match enum values
                    platform_enum = PlatformEnum(platform_name.upper())
                    platform_enums.append(platform_enum)
                except ValueError:
                    raise ValueError(f"Invalid platform: {platform_name}")
            
            # Validate user has authenticated with all platforms
            await self._validate_platform_auth(db, user_id, platforms)
            
            schedule.platforms = platform_enums
        
        # Update post config if provided
        if post_config is not None:
            schedule.post_config = post_config
        
        # Update recurrence pattern if provided
        if recurrence_pattern is not None:
            self._validate_recurrence_pattern(recurrence_pattern)
            schedule.recurrence_pattern = recurrence_pattern
        
        schedule.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(schedule)
        
        logger.info(f"Updated schedule {schedule_id}")
        
        return schedule
    
    async def get_upcoming_schedules(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 50,
        include_inactive: bool = False
    ) -> List[Schedule]:
        """Get user's upcoming schedules
        
        Args:
            db: Database session
            user_id: User ID
            limit: Maximum number of schedules to return
            include_inactive: Whether to include cancelled schedules
            
        Returns:
            List of Schedule objects ordered by scheduled time
        """
        query = select(Schedule).where(Schedule.user_id == user_id)
        
        # Filter by active status
        if not include_inactive:
            query = query.where(Schedule.is_active == True)
        
        # Order by scheduled time (earliest first)
        query = query.order_by(Schedule.scheduled_at)
        
        # Apply limit
        query = query.limit(limit)
        
        result = await db.execute(query)
        schedules = result.scalars().all()
        
        return list(schedules)
    
    async def get_schedule(
        self,
        db: AsyncSession,
        schedule_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[Schedule]:
        """Get a specific schedule
        
        Args:
            db: Database session
            schedule_id: Schedule ID
            user_id: User ID (for authorization)
            
        Returns:
            Schedule object or None if not found
            
        Raises:
            ValueError: If schedule doesn't belong to user
        """
        query = select(Schedule).where(Schedule.id == schedule_id)
        result = await db.execute(query)
        schedule = result.scalar_one_or_none()
        
        if schedule and schedule.user_id != user_id:
            raise ValueError("Schedule does not belong to user")
        
        return schedule
    
    async def get_due_schedules(
        self,
        db: AsyncSession,
        window_seconds: int = 60
    ) -> List[Schedule]:
        """Get schedules that are due to be executed
        
        Args:
            db: Database session
            window_seconds: Time window in seconds (schedules due within this window)
            
        Returns:
            List of Schedule objects that need to be executed
        """
        now = datetime.utcnow()
        window_end = now + timedelta(seconds=window_seconds)
        
        query = select(Schedule).where(
            and_(
                Schedule.is_active == True,
                Schedule.scheduled_at <= window_end,
                Schedule.scheduled_at > now - timedelta(seconds=window_seconds)
            )
        ).order_by(Schedule.scheduled_at)
        
        result = await db.execute(query)
        schedules = result.scalars().all()
        
        return list(schedules)
    
    def calculate_next_occurrence(
        self,
        recurrence_pattern: str,
        from_time: Optional[datetime] = None
    ) -> datetime:
        """Calculate next occurrence time for a recurring schedule
        
        Args:
            recurrence_pattern: Cron-like pattern
            from_time: Calculate from this time (defaults to now)
            
        Returns:
            Next occurrence datetime
            
        Raises:
            ValueError: If pattern is invalid
        """
        if from_time is None:
            from_time = datetime.utcnow()
        
        try:
            cron = croniter(recurrence_pattern, from_time)
            return cron.get_next(datetime)
        except Exception as e:
            raise ValueError(f"Invalid recurrence pattern: {e}")
    
    async def _get_video(
        self,
        db: AsyncSession,
        video_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[Video]:
        """Get video by ID and validate ownership
        
        Args:
            db: Database session
            video_id: Video ID
            user_id: User ID
            
        Returns:
            Video object or None
        """
        query = select(Video).where(
            and_(
                Video.id == video_id,
                Video.user_id == user_id
            )
        )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def _validate_platform_auth(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        platforms: List[str]
    ) -> None:
        """Validate user has authenticated with all specified platforms
        
        Args:
            db: Database session
            user_id: User ID
            platforms: List of platform names
            
        Raises:
            ValueError: If user is not authenticated with any platform
        """
        for platform_name in platforms:
            # Convert to uppercase to match enum values
            platform_enum = PlatformEnum(platform_name.upper())
            
            query = select(PlatformAuth).where(
                and_(
                    PlatformAuth.user_id == user_id,
                    PlatformAuth.platform == platform_enum,
                    PlatformAuth.is_active == True
                )
            )
            
            result = await db.execute(query)
            auth = result.scalar_one_or_none()
            
            if not auth:
                raise ValueError(
                    f"User is not authenticated with {platform_name}. "
                    f"Please connect your {platform_name} account first."
                )
            
            # Check if token is expired
            if auth.token_expires_at <= datetime.utcnow():
                raise ValueError(
                    f"Your {platform_name} authentication has expired. "
                    f"Please reconnect your account."
                )
    
    def _validate_recurrence_pattern(self, pattern: str) -> None:
        """Validate cron-like recurrence pattern
        
        Args:
            pattern: Cron pattern string
            
        Raises:
            ValueError: If pattern is invalid
        """
        try:
            # Test if pattern is valid by creating a croniter instance
            cron = croniter(pattern, datetime.utcnow())
            # Try to get next occurrence to ensure pattern works
            cron.get_next(datetime)
        except Exception as e:
            raise ValueError(
                f"Invalid recurrence pattern '{pattern}'. "
                f"Expected cron format (e.g., '0 9 * * 1' for every Monday at 9am). "
                f"Error: {e}"
            )
