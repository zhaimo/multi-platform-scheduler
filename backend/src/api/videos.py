"""Video management API endpoints"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.database import get_db
from src.services.video_service import VideoService
from src.services.s3_service import S3Service
from src.config import get_settings
from src.utils.auth import get_current_user
from src.utils.validators import FileValidator, InputSanitizer
from src.models.database_models import User

router = APIRouter(prefix="/api/videos", tags=["videos"])


# Helper functions
def _convert_to_presigned_url(s3_url: str, s3_service: S3Service) -> str:
    """Convert S3 URL to presigned URL for browser access
    
    Args:
        s3_url: S3 URL in format s3://bucket/key
        s3_service: S3 service instance
        
    Returns:
        Presigned URL that can be accessed by browsers
    """
    if not s3_url or not s3_url.startswith('s3://'):
        return s3_url
    
    # Extract object key from S3 URL
    # Format: s3://bucket-name/path/to/object
    parts = s3_url.replace('s3://', '').split('/', 1)
    if len(parts) < 2:
        return s3_url
    
    object_key = parts[1]
    
    # Generate presigned URL (valid for 1 hour)
    return s3_service.generate_presigned_download_url(object_key, expiration=3600)


# Pydantic schemas
class VideoResponse(BaseModel):
    """Video response schema"""
    id: UUID
    user_id: UUID
    title: str
    description: Optional[str]
    file_url: str
    thumbnail_url: Optional[str]
    duration: int
    format: str
    resolution: str
    file_size: int
    tags: List[str]
    category: Optional[str]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class VideoUpdateRequest(BaseModel):
    """Video update request schema"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    tags: Optional[List[str]] = Field(None, max_items=20)
    category: Optional[str] = Field(None, max_length=100)


class VideoListResponse(BaseModel):
    """Video list response schema"""
    videos: List[VideoResponse]
    total: int


# Dependency to get services
def get_video_service() -> VideoService:
    """Get video service instance"""
    settings = get_settings()
    s3_service = S3Service(settings)
    return VideoService(settings, s3_service)


@router.post("/upload", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    file: UploadFile = File(..., description="Video file to upload"),
    title: str = Form(..., min_length=1, max_length=255),
    description: Optional[str] = Form(None, max_length=2000),
    tags: Optional[str] = Form(None, description="Comma-separated tags"),
    category: Optional[str] = Form(None, max_length=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    video_service: VideoService = Depends(get_video_service)
):
    """Upload a new video
    
    Args:
        file: Video file (MP4, MOV, AVI, WebM)
        title: Video title
        description: Optional video description
        tags: Optional comma-separated tags
        category: Optional category
        current_user: Authenticated user
        db: Database session
        video_service: Video service instance
        
    Returns:
        Created video object
    """
    # Validate file
    await FileValidator.validate_video_file(file)
    
    # Sanitize filename
    file.filename = FileValidator.sanitize_filename(file.filename)
    
    # Sanitize text inputs
    title = InputSanitizer.sanitize_text(title, max_length=255)
    description = InputSanitizer.sanitize_text(description, max_length=2000) if description else None
    category = InputSanitizer.sanitize_text(category, max_length=100) if category else None
    
    # Parse and sanitize tags from comma-separated string
    tags_list = [tag.strip() for tag in tags.split(",")] if tags else []
    tags_list = InputSanitizer.sanitize_tags(tags_list)
    
    try:
        video = await video_service.upload_video(
            db=db,
            user_id=current_user.id,
            file=file,
            title=title,
            description=description,
            tags=tags_list,
            category=category
        )
        
        # Convert S3 URLs to presigned URLs
        settings = get_settings()
        s3_service = S3Service(settings)
        
        return VideoResponse(
            id=video.id,
            user_id=video.user_id,
            title=video.title,
            description=video.description,
            file_url=_convert_to_presigned_url(video.file_url, s3_service),
            thumbnail_url=_convert_to_presigned_url(video.thumbnail_url, s3_service) if video.thumbnail_url else None,
            duration=video.duration,
            format=video.format,
            resolution=video.resolution,
            file_size=video.file_size,
            tags=video.tags,
            category=video.category,
            created_at=video.created_at.isoformat(),
            updated_at=video.updated_at.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload video: {str(e)}"
        )


@router.get("", response_model=List[VideoResponse])
async def list_videos(
    tags: Optional[str] = Query(None, description="Comma-separated tags to filter by"),
    category: Optional[str] = Query(None, description="Category to filter by"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    video_service: VideoService = Depends(get_video_service)
):
    """List user's videos with optional filtering
    
    Args:
        tags: Comma-separated tags to filter by
        category: Category to filter by
        search: Search query for title and description
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        current_user: Authenticated user
        db: Database session
        video_service: Video service instance
        
    Returns:
        List of video objects
    """
    # Parse tags from comma-separated string
    tags_list = [tag.strip() for tag in tags.split(",")] if tags else None
    
    videos = await video_service.get_user_videos(
        db=db,
        user_id=current_user.id,
        tags=tags_list,
        category=category,
        search=search,
        skip=skip,
        limit=limit
    )
    
    # Convert S3 URLs to presigned URLs
    settings = get_settings()
    s3_service = S3Service(settings)
    
    return [
        VideoResponse(
            id=video.id,
            user_id=video.user_id,
            title=video.title,
            description=video.description,
            file_url=_convert_to_presigned_url(video.file_url, s3_service),
            thumbnail_url=_convert_to_presigned_url(video.thumbnail_url, s3_service) if video.thumbnail_url else None,
            duration=video.duration,
            format=video.format,
            resolution=video.resolution,
            file_size=video.file_size,
            tags=video.tags,
            category=video.category,
            created_at=video.created_at.isoformat(),
            updated_at=video.updated_at.isoformat()
        )
        for video in videos
    ]


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    video_service: VideoService = Depends(get_video_service)
):
    """Get a specific video by ID
    
    Args:
        video_id: Video ID
        current_user: Authenticated user
        db: Database session
        video_service: Video service instance
        
    Returns:
        Video object
    """
    video = await video_service.get_video_by_id(
        db=db,
        video_id=video_id,
        user_id=current_user.id
    )
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    # Convert S3 URLs to presigned URLs
    settings = get_settings()
    s3_service = S3Service(settings)
    
    return VideoResponse(
        id=video.id,
        user_id=video.user_id,
        title=video.title,
        description=video.description,
        file_url=_convert_to_presigned_url(video.file_url, s3_service),
        thumbnail_url=_convert_to_presigned_url(video.thumbnail_url, s3_service) if video.thumbnail_url else None,
        duration=video.duration,
        format=video.format,
        resolution=video.resolution,
        file_size=video.file_size,
        tags=video.tags,
        category=video.category,
        created_at=video.created_at.isoformat(),
        updated_at=video.updated_at.isoformat()
    )


@router.patch("/{video_id}", response_model=VideoResponse)
async def update_video(
    video_id: UUID,
    update_data: VideoUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    video_service: VideoService = Depends(get_video_service)
):
    """Update video metadata
    
    Args:
        video_id: Video ID
        update_data: Fields to update
        current_user: Authenticated user
        db: Database session
        video_service: Video service instance
        
    Returns:
        Updated video object
    """
    video = await video_service.update_video(
        db=db,
        video_id=video_id,
        user_id=current_user.id,
        title=update_data.title,
        description=update_data.description,
        tags=update_data.tags,
        category=update_data.category
    )
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    # Convert S3 URLs to presigned URLs
    settings = get_settings()
    s3_service = S3Service(settings)
    
    return VideoResponse(
        id=video.id,
        user_id=video.user_id,
        title=video.title,
        description=video.description,
        file_url=_convert_to_presigned_url(video.file_url, s3_service),
        thumbnail_url=_convert_to_presigned_url(video.thumbnail_url, s3_service) if video.thumbnail_url else None,
        duration=video.duration,
        format=video.format,
        resolution=video.resolution,
        file_size=video.file_size,
        tags=video.tags,
        category=video.category,
        created_at=video.created_at.isoformat(),
        updated_at=video.updated_at.isoformat()
    )


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    video_service: VideoService = Depends(get_video_service)
):
    """Delete a video
    
    Args:
        video_id: Video ID
        current_user: Authenticated user
        db: Database session
        video_service: Video service instance
        
    Returns:
        No content on success
    """
    deleted = await video_service.delete_video(
        db=db,
        video_id=video_id,
        user_id=current_user.id
    )
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    return None


class PlatformAnalytics(BaseModel):
    """Analytics for a specific platform"""
    platform: str
    views: int
    likes: int
    comments: int
    shares: int
    synced_at: str


class VideoAnalyticsResponse(BaseModel):
    """Aggregated video analytics response"""
    video_id: UUID
    total_views: int
    total_likes: int
    total_comments: int
    total_shares: int
    platforms: List[PlatformAnalytics]


@router.get("/{video_id}/analytics", response_model=VideoAnalyticsResponse)
async def get_video_analytics(
    video_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    video_service: VideoService = Depends(get_video_service)
):
    """Get aggregated analytics for a video across all platforms
    
    Args:
        video_id: Video ID
        current_user: Authenticated user
        db: Database session
        video_service: Video service instance
        
    Returns:
        Aggregated analytics with per-platform breakdown
    """
    # Verify video exists and belongs to user
    video = await video_service.get_video_by_id(
        db=db,
        video_id=video_id,
        user_id=current_user.id
    )
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    # Get analytics from database
    from sqlalchemy import select
    from src.models.database_models import VideoAnalytics as VideoAnalyticsModel
    
    result = await db.execute(
        select(VideoAnalyticsModel).where(
            VideoAnalyticsModel.video_id == video_id
        )
    )
    analytics_records = result.scalars().all()
    
    # Aggregate metrics
    total_views = 0
    total_likes = 0
    total_comments = 0
    total_shares = 0
    platforms = []
    
    for record in analytics_records:
        total_views += record.views
        total_likes += record.likes
        total_comments += record.comments
        total_shares += record.shares
        
        platforms.append(PlatformAnalytics(
            platform=record.platform.value,
            views=record.views,
            likes=record.likes,
            comments=record.comments,
            shares=record.shares,
            synced_at=record.synced_at.isoformat()
        ))
    
    return VideoAnalyticsResponse(
        video_id=video_id,
        total_views=total_views,
        total_likes=total_likes,
        total_comments=total_comments,
        total_shares=total_shares,
        platforms=platforms
    )
