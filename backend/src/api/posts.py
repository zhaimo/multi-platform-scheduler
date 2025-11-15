"""Post management API endpoints"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.database import get_db
from src.services.post_service import PostService
from src.adapters.tiktok import TikTokAdapter
from src.config import get_settings
from src.utils.auth import get_current_user
from src.utils.validators import InputSanitizer
from src.models.database_models import User, PostStatusEnum, PostTemplate
from src.tasks import post_video
from sqlalchemy import select

router = APIRouter(prefix="/api/posts", tags=["posts"])


# Pydantic schemas
class PlatformConfigRequest(BaseModel):
    """Platform-specific configuration"""
    caption: str = Field(..., min_length=1, description="Post caption")
    hashtags: List[str] = Field(default_factory=list, description="List of hashtags")
    privacy_level: str = Field(default="public", description="Privacy level (public, private, friends)")
    disable_comments: bool = Field(default=False, description="Disable comments")
    disable_duet: bool = Field(default=False, description="Disable duet (TikTok)")
    disable_stitch: bool = Field(default=False, description="Disable stitch (TikTok)")


class CreatePostRequest(BaseModel):
    """Create post request schema"""
    video_id: UUID = Field(..., description="ID of the video to post")
    platforms: Optional[Dict[str, PlatformConfigRequest]] = Field(
        None,
        description="Platform-specific configurations (e.g., {'tiktok': {...}, 'youtube': {...}}). Required if template_id is not provided."
    )
    template_id: Optional[UUID] = Field(
        None,
        description="ID of a template to use for platform configurations. If provided, platforms will be auto-populated from the template."
    )
    scheduled_at: Optional[datetime] = Field(None, description="Optional scheduled posting time")
    
    class Config:
        json_schema_extra = {
            "example": {
                "video_id": "123e4567-e89b-12d3-a456-426614174000",
                "platforms": {
                    "tiktok": {
                        "caption": "Check out this amazing video! #viral #trending",
                        "hashtags": ["viral", "trending", "fyp"],
                        "privacy_level": "public",
                        "disable_comments": False
                    }
                },
                "template_id": None,
                "scheduled_at": None
            }
        }


class PostResponse(BaseModel):
    """Post response schema"""
    id: UUID
    user_id: UUID
    video_id: UUID
    multi_post_id: Optional[UUID]
    platform: str
    status: str
    platform_post_id: Optional[str]
    platform_url: Optional[str]
    caption: str
    hashtags: List[str]
    scheduled_at: Optional[str]
    posted_at: Optional[str]
    error_message: Optional[str]
    retry_count: int
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class MultiPostResponse(BaseModel):
    """Multi-post response schema"""
    id: UUID
    user_id: UUID
    video_id: UUID
    posts: List[PostResponse]
    created_at: str
    
    class Config:
        from_attributes = True


# Dependency to get services
def get_post_service() -> PostService:
    """Get post service instance"""
    settings = get_settings()
    
    # Initialize platform adapters
    platform_adapters = {}
    
    # TikTok adapter
    if settings.tiktok_client_id and settings.tiktok_client_secret:
        platform_adapters["tiktok"] = TikTokAdapter(
            client_id=settings.tiktok_client_id,
            client_secret=settings.tiktok_client_secret,
            redirect_uri=settings.tiktok_redirect_uri
        )
    
    # YouTube adapter
    from src.adapters.youtube import YouTubeAdapter
    if settings.youtube_client_id and settings.youtube_client_secret:
        platform_adapters["youtube"] = YouTubeAdapter(
            client_id=settings.youtube_client_id,
            client_secret=settings.youtube_client_secret,
            redirect_uri=settings.youtube_redirect_uri
        )
    
    # Instagram adapter
    from src.adapters.instagram import InstagramAdapter
    if settings.instagram_client_id and settings.instagram_client_secret:
        platform_adapters["instagram"] = InstagramAdapter(
            client_id=settings.instagram_client_id,
            client_secret=settings.instagram_client_secret,
            redirect_uri=settings.instagram_redirect_uri
        )
    
    # Facebook adapter
    from src.adapters.facebook import FacebookAdapter
    if settings.facebook_client_id and settings.facebook_client_secret:
        platform_adapters["facebook"] = FacebookAdapter(
            client_id=settings.facebook_client_id,
            client_secret=settings.facebook_client_secret,
            redirect_uri=settings.facebook_redirect_uri
        )
    
    # Twitter adapter
    from src.adapters.twitter import TwitterAdapter
    if settings.twitter_client_id and settings.twitter_client_secret:
        platform_adapters["twitter"] = TwitterAdapter(
            client_id=settings.twitter_client_id,
            client_secret=settings.twitter_client_secret,
            redirect_uri=settings.twitter_redirect_uri
        )
    
    return PostService(settings, platform_adapters)


@router.post("", response_model=MultiPostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    request: CreatePostRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    post_service: PostService = Depends(get_post_service)
):
    """Create a new post for one or more platforms
    
    This endpoint creates Post records for each specified platform and queues
    them for immediate or scheduled execution.
    
    You can either:
    - Provide platform configurations directly via the 'platforms' parameter
    - Use a saved template by providing 'template_id' to auto-populate platform configurations
    
    Args:
        request: Post creation request with video ID and platform configs or template_id
        current_user: Authenticated user
        db: Database session
        post_service: Post service instance
        
    Returns:
        Created multi-post object with all associated posts
    """
    try:
        # Log the incoming request for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Create post request: video_id={request.video_id}, platforms={request.platforms}, template_id={request.template_id}, scheduled_at={request.scheduled_at}")
        logger.info(f"Available platform adapters: {list(post_service.platform_adapters.keys())}")
        
        # Validate that either platforms or template_id is provided
        if not request.platforms and not request.template_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'platforms' or 'template_id' must be provided"
            )
        
        # If template_id is provided, load template and use its configurations
        platform_configs = {}
        if request.template_id:
            # Load template
            result = await db.execute(
                select(PostTemplate)
                .where(
                    PostTemplate.id == request.template_id,
                    PostTemplate.user_id == current_user.id
                )
            )
            template = result.scalar_one_or_none()
            
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template not found"
                )
            
            # Use template configurations
            platform_configs = template.platform_configs
            
            # If platforms are also provided, merge them (platforms override template)
            if request.platforms:
                for platform_name, config in request.platforms.items():
                    platform_configs[platform_name] = {
                        "caption": config.caption,
                        "hashtags": config.hashtags,
                        "privacy_level": config.privacy_level,
                        "disable_comments": config.disable_comments,
                        "disable_duet": config.disable_duet,
                        "disable_stitch": config.disable_stitch
                    }
        else:
            # Convert PlatformConfigRequest to dict format expected by service
            for platform_name, config in request.platforms.items():
                # Sanitize caption and hashtags
                sanitized_caption = InputSanitizer.sanitize_text(config.caption, max_length=5000)
                sanitized_hashtags = InputSanitizer.sanitize_hashtags(config.hashtags)
                
                platform_configs[platform_name] = {
                    "caption": sanitized_caption,
                    "hashtags": sanitized_hashtags,
                    "privacy_level": config.privacy_level,
                    "disable_comments": config.disable_comments,
                    "disable_duet": config.disable_duet,
                    "disable_stitch": config.disable_stitch
                }
        
        # Create multi-post
        multi_post = await post_service.create_multi_post(
            db=db,
            user_id=current_user.id,
            video_id=request.video_id,
            platform_configs=platform_configs,
            scheduled_at=request.scheduled_at
        )
        
        # Queue PostVideoJob for each post
        for post in multi_post.posts:
            if request.scheduled_at:
                # Schedule for future execution
                post_video.apply_async(
                    args=[str(post.id)],
                    eta=request.scheduled_at
                )
            else:
                # Execute immediately
                post_video.delay(str(post.id))
        
        # Convert to response format
        posts_response = [
            PostResponse(
                id=post.id,
                user_id=post.user_id,
                video_id=post.video_id,
                multi_post_id=post.multi_post_id,
                platform=post.platform.value,
                status=post.status.value,
                platform_post_id=post.platform_post_id,
                platform_url=post.platform_url,
                caption=post.caption,
                hashtags=post.hashtags,
                scheduled_at=post.scheduled_at.isoformat() if post.scheduled_at else None,
                posted_at=post.posted_at.isoformat() if post.posted_at else None,
                error_message=post.error_message,
                retry_count=post.retry_count,
                created_at=post.created_at.isoformat(),
                updated_at=post.updated_at.isoformat()
            )
            for post in multi_post.posts
        ]
        
        return MultiPostResponse(
            id=multi_post.id,
            user_id=multi_post.user_id,
            video_id=multi_post.video_id,
            posts=posts_response,
            created_at=multi_post.created_at.isoformat()
        )
        
    except ValueError as e:
        logger.error(f"ValueError in create_post: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Exception in create_post: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create post: {str(e)}"
        )


@router.get("", response_model=List[PostResponse])
async def list_posts(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    video_id: Optional[UUID] = Query(None, description="Filter by video ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    post_service: PostService = Depends(get_post_service)
):
    """List user's posts with optional filtering
    
    Args:
        platform: Filter by platform (tiktok, youtube, instagram, facebook)
        status_filter: Filter by status (pending, processing, posted, failed, cancelled)
        video_id: Filter by video ID
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        current_user: Authenticated user
        db: Database session
        post_service: Post service instance
        
    Returns:
        List of post objects
    """
    try:
        posts = await post_service.get_user_posts(
            db=db,
            user_id=current_user.id,
            platform=platform,
            status=status_filter,
            video_id=video_id,
            skip=skip,
            limit=limit
        )
        
        return [
            PostResponse(
                id=post.id,
                user_id=post.user_id,
                video_id=post.video_id,
                multi_post_id=post.multi_post_id,
                platform=post.platform.value,
                status=post.status.value,
                platform_post_id=post.platform_post_id,
                platform_url=post.platform_url,
                caption=post.caption,
                hashtags=post.hashtags,
                scheduled_at=post.scheduled_at.isoformat() if post.scheduled_at else None,
                posted_at=post.posted_at.isoformat() if post.posted_at else None,
                error_message=post.error_message,
                retry_count=post.retry_count,
                created_at=post.created_at.isoformat(),
                updated_at=post.updated_at.isoformat()
            )
            for post in posts
        ]
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    post_service: PostService = Depends(get_post_service)
):
    """Get a specific post by ID
    
    Args:
        post_id: Post ID
        current_user: Authenticated user
        db: Database session
        post_service: Post service instance
        
    Returns:
        Post object
    """
    post = await post_service.get_post_status(
        db=db,
        post_id=post_id,
        user_id=current_user.id
    )
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    return PostResponse(
        id=post.id,
        user_id=post.user_id,
        video_id=post.video_id,
        multi_post_id=post.multi_post_id,
        platform=post.platform.value,
        status=post.status.value,
        platform_post_id=post.platform_post_id,
        platform_url=post.platform_url,
        caption=post.caption,
        hashtags=post.hashtags,
        scheduled_at=post.scheduled_at.isoformat() if post.scheduled_at else None,
        posted_at=post.posted_at.isoformat() if post.posted_at else None,
        error_message=post.error_message,
        retry_count=post.retry_count,
        created_at=post.created_at.isoformat(),
        updated_at=post.updated_at.isoformat()
    )


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    post_service: PostService = Depends(get_post_service)
):
    """Cancel a pending or scheduled post
    
    Args:
        post_id: Post ID
        current_user: Authenticated user
        db: Database session
        post_service: Post service instance
        
    Returns:
        No content on success
    """
    post = await post_service.get_post_status(
        db=db,
        post_id=post_id,
        user_id=current_user.id
    )
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Allow deletion of pending, failed, and posted posts
    # Processing posts cannot be deleted (they're actively being posted)
    if post.status == PostStatusEnum.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete post with status '{post.status.value}'. Post is currently being processed."
        )
    
    # For pending posts, mark as cancelled
    # For other statuses (posted, failed), delete the record
    if post.status == PostStatusEnum.PENDING:
        post.status = PostStatusEnum.CANCELLED
        await db.commit()
    else:
        # Delete the post record for posted/failed posts
        await db.delete(post)
        await db.commit()
    
    return None


class RepostRequest(BaseModel):
    """Repost request schema"""
    platforms: Optional[Dict[str, PlatformConfigRequest]] = Field(
        None,
        description="Optional platform-specific configurations. If not provided, uses original post metadata or template."
    )
    template_id: Optional[UUID] = Field(
        None,
        description="ID of a template to use for platform configurations. If provided, platforms will be auto-populated from the template."
    )
    scheduled_at: Optional[datetime] = Field(None, description="Optional scheduled posting time")
    
    class Config:
        json_schema_extra = {
            "example": {
                "platforms": {
                    "tiktok": {
                        "caption": "Reposting this amazing video! #throwback #viral",
                        "hashtags": ["throwback", "viral", "fyp"],
                        "privacy_level": "public",
                        "disable_comments": False
                    }
                },
                "template_id": None,
                "scheduled_at": None
            }
        }


@router.post("/{post_id}/repost", response_model=MultiPostResponse, status_code=status.HTTP_201_CREATED)
async def repost_video(
    post_id: UUID,
    request: RepostRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    post_service: PostService = Depends(get_post_service)
):
    """Repost a previously posted video with optional modifications
    
    This endpoint allows reposting a video that was previously posted. You can:
    - Use the original post metadata (caption, hashtags) by not providing platforms or template_id
    - Use a saved template by providing 'template_id' to auto-populate platform configurations
    - Modify the caption, hashtags, and other settings by providing platform configs
    - Post to different platforms than the original post
    - Schedule the repost for a future time
    
    The 24-hour repost restriction per platform is enforced.
    
    Args:
        post_id: ID of the original post to repost
        request: Repost request with optional platform configs or template_id
        current_user: Authenticated user
        db: Database session
        post_service: Post service instance
        
    Returns:
        Created multi-post object with all associated posts
    """
    try:
        # If template_id is provided, load template and use its configurations
        platform_configs = {}
        if request.template_id:
            # Load template
            result = await db.execute(
                select(PostTemplate)
                .where(
                    PostTemplate.id == request.template_id,
                    PostTemplate.user_id == current_user.id
                )
            )
            template = result.scalar_one_or_none()
            
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template not found"
                )
            
            # Use template configurations
            platform_configs = template.platform_configs
            
            # If platforms are also provided, merge them (platforms override template)
            if request.platforms:
                for platform_name, config in request.platforms.items():
                    platform_configs[platform_name] = {
                        "caption": config.caption,
                        "hashtags": config.hashtags,
                        "privacy_level": config.privacy_level,
                        "disable_comments": config.disable_comments,
                        "disable_duet": config.disable_duet,
                        "disable_stitch": config.disable_stitch
                    }
        elif request.platforms:
            # Convert PlatformConfigRequest to dict format expected by service
            for platform_name, config in request.platforms.items():
                platform_configs[platform_name] = {
                    "caption": config.caption,
                    "hashtags": config.hashtags,
                    "privacy_level": config.privacy_level,
                    "disable_comments": config.disable_comments,
                    "disable_duet": config.disable_duet,
                    "disable_stitch": config.disable_stitch
                }
        
        # Create repost
        multi_post = await post_service.repost_video(
            db=db,
            user_id=current_user.id,
            post_id=post_id,
            platform_configs=platform_configs,
            scheduled_at=request.scheduled_at
        )
        
        # Queue PostVideoJob for each post
        for post in multi_post.posts:
            if request.scheduled_at:
                # Schedule for future execution
                post_video.apply_async(
                    args=[str(post.id)],
                    eta=request.scheduled_at
                )
            else:
                # Execute immediately
                post_video.delay(str(post.id))
        
        # Convert to response format
        posts_response = [
            PostResponse(
                id=post.id,
                user_id=post.user_id,
                video_id=post.video_id,
                multi_post_id=post.multi_post_id,
                platform=post.platform.value,
                status=post.status.value,
                platform_post_id=post.platform_post_id,
                platform_url=post.platform_url,
                caption=post.caption,
                hashtags=post.hashtags,
                scheduled_at=post.scheduled_at.isoformat() if post.scheduled_at else None,
                posted_at=post.posted_at.isoformat() if post.posted_at else None,
                error_message=post.error_message,
                retry_count=post.retry_count,
                created_at=post.created_at.isoformat(),
                updated_at=post.updated_at.isoformat()
            )
            for post in multi_post.posts
        ]
        
        return MultiPostResponse(
            id=multi_post.id,
            user_id=multi_post.user_id,
            video_id=multi_post.video_id,
            posts=posts_response,
            created_at=multi_post.created_at.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create repost: {str(e)}"
        )
