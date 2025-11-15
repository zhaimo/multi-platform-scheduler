"""Post management service"""

import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc

from src.models.database_models import (
    Post,
    MultiPost,
    Video,
    PlatformConnection,
    PlatformEnum,
    PostStatusEnum,
    User
)
from src.adapters.base import PlatformAdapter, PlatformLimits
from src.config import Settings

logger = logging.getLogger(__name__)


class PostService:
    """Service for managing posts across multiple platforms"""
    
    def __init__(self, settings: Settings, platform_adapters: Dict[str, PlatformAdapter]):
        """Initialize post service
        
        Args:
            settings: Application settings
            platform_adapters: Dictionary mapping platform names to adapter instances
        """
        self.settings = settings
        self.platform_adapters = platform_adapters
    
    async def create_multi_post(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        video_id: uuid.UUID,
        platform_configs: Dict[str, Dict[str, Any]],
        scheduled_at: Optional[datetime] = None
    ) -> MultiPost:
        """Create posts for multiple platforms
        
        Args:
            db: Database session
            user_id: ID of the user creating the post
            video_id: ID of the video to post
            platform_configs: Dictionary mapping platform names to their configs
                Example: {
                    "tiktok": {"caption": "...", "hashtags": [...], "privacy_level": "public"},
                    "youtube": {"caption": "...", "hashtags": [...]}
                }
            scheduled_at: Optional datetime to schedule the post
            
        Returns:
            Created MultiPost object with associated Post records
            
        Raises:
            ValueError: If validation fails
        """
        # Validate video exists and belongs to user
        video = await self._get_video(db, video_id, user_id)
        if not video:
            raise ValueError(f"Video not found or does not belong to user: {video_id}")
        
        # Validate platforms
        platforms = list(platform_configs.keys())
        if not platforms:
            raise ValueError("At least one platform must be specified")
        
        # Validate user has authenticated with all platforms
        await self._validate_platform_auth(db, user_id, platforms)
        
        # Validate platform-specific caption limits
        self._validate_platform_configs(platform_configs)
        
        # Check 24-hour repost prevention
        await self._check_repost_restriction(db, user_id, video_id, platforms)
        
        # Create MultiPost record
        multi_post = MultiPost(
            id=uuid.uuid4(),
            user_id=user_id,
            video_id=video_id
        )
        db.add(multi_post)
        await db.flush()  # Get the multi_post.id
        
        # Create Post records for each platform
        posts = []
        for platform_name, config in platform_configs.items():
            # Convert to uppercase to match enum values
            platform_enum = PlatformEnum(platform_name.upper())
            
            post = Post(
                id=uuid.uuid4(),
                user_id=user_id,
                video_id=video_id,
                multi_post_id=multi_post.id,
                platform=platform_enum,
                status=PostStatusEnum.PENDING,
                caption=config.get("caption", ""),
                hashtags=config.get("hashtags", []),
                scheduled_at=scheduled_at,
                retry_count=0
            )
            
            db.add(post)
            posts.append(post)
        
        await db.commit()
        
        # Reload multi_post with posts relationship
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(MultiPost)
            .options(selectinload(MultiPost.posts))
            .where(MultiPost.id == multi_post.id)
        )
        multi_post = result.scalar_one()
        
        logger.info(
            f"Created multi-post {multi_post.id} with {len(posts)} posts for video {video_id}"
        )
        
        return multi_post
    
    async def get_post_status(
        self,
        db: AsyncSession,
        post_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[Post]:
        """Get status of a specific post
        
        Args:
            db: Database session
            post_id: Post ID
            user_id: User ID (for authorization)
            
        Returns:
            Post object or None if not found
        """
        query = select(Post).where(
            and_(
                Post.id == post_id,
                Post.user_id == user_id
            )
        )
        
        result = await db.execute(query)
        post = result.scalar_one_or_none()
        
        return post
    
    async def get_user_posts(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        video_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Post]:
        """Get user's posts with optional filtering
        
        Args:
            db: Database session
            user_id: User ID
            platform: Filter by platform
            status: Filter by status
            video_id: Filter by video ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Post objects
        """
        query = select(Post).where(Post.user_id == user_id)
        
        # Apply filters
        if platform:
            # Convert to uppercase to match enum values
            platform_enum = PlatformEnum(platform.upper())
            query = query.where(Post.platform == platform_enum)
        
        if status:
            status_enum = PostStatusEnum(status)
            query = query.where(Post.status == status_enum)
        
        if video_id:
            query = query.where(Post.video_id == video_id)
        
        # Order by creation date (newest first)
        query = query.order_by(desc(Post.created_at))
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        posts = result.scalars().all()
        
        return list(posts)
    
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
            
            query = select(PlatformConnection).where(
                and_(
                    PlatformConnection.user_id == user_id,
                    PlatformConnection.platform == platform_enum,
                    PlatformConnection.is_active == True
                )
            )
            
            result = await db.execute(query)
            auth = result.scalar_one_or_none()
            
            if not auth:
                raise ValueError(
                    f"User is not authenticated with {platform_name}. "
                    f"Please connect your {platform_name} account first."
                )
            
            # Check if token is expired and refresh if possible
            if auth.token_expires_at and auth.token_expires_at <= datetime.utcnow():
                if auth.refresh_token:
                    # Attempt to refresh the token
                    try:
                        adapter = self._get_adapter(platform_name)
                        new_tokens = await adapter.refresh_token(auth.refresh_token)
                        
                        # Update the connection with new tokens
                        auth.access_token = new_tokens.access_token
                        auth.token_expires_at = new_tokens.expires_at
                        if new_tokens.refresh_token:
                            auth.refresh_token = new_tokens.refresh_token
                        
                        await db.commit()
                        logger.info(f"Successfully refreshed {platform_name} token for user {user_id}")
                    except Exception as e:
                        logger.error(f"Failed to refresh {platform_name} token: {str(e)}")
                        raise ValueError(
                            f"Your {platform_name} authentication has expired and could not be refreshed. "
                            f"Please reconnect your account."
                        )
                else:
                    raise ValueError(
                        f"Your {platform_name} authentication has expired. "
                        f"Please reconnect your account."
                    )
    
    def _get_adapter(self, platform_name: str) -> PlatformAdapter:
        """Get platform adapter by name
        
        Args:
            platform_name: Name of the platform
            
        Returns:
            PlatformAdapter instance
            
        Raises:
            ValueError: If platform is not supported
        """
        # Convert to lowercase for lookup
        platform_key = platform_name.lower()
        logger.debug(f"Looking up adapter for platform: {platform_name} (key: {platform_key})")
        logger.debug(f"Available adapters: {list(self.platform_adapters.keys())}")
        adapter = self.platform_adapters.get(platform_key)
        if not adapter:
            raise ValueError(f"Unsupported platform: {platform_name}")
        return adapter
    
    def _validate_platform_configs(
        self,
        platform_configs: Dict[str, Dict[str, Any]]
    ) -> None:
        """Validate platform-specific configurations
        
        Args:
            platform_configs: Dictionary of platform configs
            
        Raises:
            ValueError: If any config is invalid
        """
        for platform_name, config in platform_configs.items():
            # Get platform adapter (convert to lowercase for lookup)
            platform_key = platform_name.lower()
            logger.debug(f"Validating config for platform: {platform_name} (key: {platform_key})")
            logger.debug(f"Available adapters: {list(self.platform_adapters.keys())}")
            adapter = self.platform_adapters.get(platform_key)
            if not adapter:
                raise ValueError(f"Unsupported platform: {platform_name}")
            
            # Get platform limits
            limits = adapter.get_platform_limits()
            
            # Validate caption length
            caption = config.get("caption", "")
            if len(caption) > limits.max_caption_length:
                raise ValueError(
                    f"{platform_name} caption exceeds maximum length of "
                    f"{limits.max_caption_length} characters. "
                    f"Current length: {len(caption)}"
                )
            
            # Validate hashtags count
            hashtags = config.get("hashtags", [])
            if len(hashtags) > limits.max_hashtags:
                raise ValueError(
                    f"{platform_name} has too many hashtags. "
                    f"Maximum: {limits.max_hashtags}, provided: {len(hashtags)}"
                )
    
    async def _check_repost_restriction(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        video_id: uuid.UUID,
        platforms: List[str]
    ) -> None:
        """Check 24-hour repost restriction for each platform
        
        Args:
            db: Database session
            user_id: User ID
            video_id: Video ID
            platforms: List of platform names
            
        Raises:
            ValueError: If repost restriction is violated
        """
        # Calculate 24 hours ago
        restriction_time = datetime.utcnow() - timedelta(hours=24)
        
        for platform_name in platforms:
            # Convert to uppercase to match enum values
            platform_enum = PlatformEnum(platform_name.upper())
            
            # Check for recent posts to this platform
            query = select(Post).where(
                and_(
                    Post.user_id == user_id,
                    Post.video_id == video_id,
                    Post.platform == platform_enum,
                    Post.status == PostStatusEnum.POSTED,
                    Post.posted_at >= restriction_time
                )
            )
            
            result = await db.execute(query)
            recent_post = result.scalar_one_or_none()
            
            if recent_post:
                time_since_post = datetime.utcnow() - recent_post.posted_at
                hours_remaining = 24 - (time_since_post.total_seconds() / 3600)
                
                raise ValueError(
                    f"Cannot repost to {platform_name}. "
                    f"This video was posted {time_since_post.total_seconds() / 3600:.1f} hours ago. "
                    f"Please wait {hours_remaining:.1f} more hours before reposting."
                )
    
    async def repost_video(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        post_id: uuid.UUID,
        platform_configs: Dict[str, Dict[str, Any]],
        scheduled_at: Optional[datetime] = None
    ) -> MultiPost:
        """Repost a previously posted video with optional modifications
        
        Args:
            db: Database session
            user_id: ID of the user creating the repost
            post_id: ID of the original post to repost
            platform_configs: Dictionary mapping platform names to their configs
                If empty, uses original post metadata
            scheduled_at: Optional datetime to schedule the repost
            
        Returns:
            Created MultiPost object with associated Post records
            
        Raises:
            ValueError: If validation fails
        """
        # Load original post
        original_post = await self.get_post_status(db, post_id, user_id)
        if not original_post:
            raise ValueError(f"Original post not found: {post_id}")
        
        # Validate original post was successfully posted
        if original_post.status != PostStatusEnum.POSTED:
            raise ValueError(
                f"Cannot repost a post that was not successfully posted. "
                f"Original post status: {original_post.status.value}"
            )
        
        # If no platform configs provided, use original post metadata
        if not platform_configs:
            platform_configs = {
                original_post.platform.value: {
                    "caption": original_post.caption,
                    "hashtags": original_post.hashtags,
                    "privacy_level": "public",
                    "disable_comments": False,
                    "disable_duet": False,
                    "disable_stitch": False
                }
            }
        
        # Validate video still exists
        video = await self._get_video(db, original_post.video_id, user_id)
        if not video:
            raise ValueError(f"Video not found: {original_post.video_id}")
        
        # Create the repost using the same logic as create_multi_post
        multi_post = await self.create_multi_post(
            db=db,
            user_id=user_id,
            video_id=original_post.video_id,
            platform_configs=platform_configs,
            scheduled_at=scheduled_at
        )
        
        logger.info(
            f"Created repost {multi_post.id} from original post {post_id} "
            f"for video {original_post.video_id}"
        )
        
        return multi_post
