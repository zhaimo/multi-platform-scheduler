"""Video management service"""

import os
import tempfile
import uuid
from typing import Optional, List
from datetime import datetime
import logging
import ffmpeg

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from src.models.database_models import Video, User
from src.services.s3_service import S3Service
from src.config import Settings

logger = logging.getLogger(__name__)


class VideoService:
    """Service for managing video uploads and metadata"""
    
    def __init__(self, settings: Settings, s3_service: S3Service):
        """Initialize video service
        
        Args:
            settings: Application settings
            s3_service: S3 service instance
        """
        self.settings = settings
        self.s3_service = s3_service
    
    async def upload_video(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        file: UploadFile,
        title: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None
    ) -> Video:
        """Upload a video file and create database record
        
        Args:
            db: Database session
            user_id: ID of the user uploading the video
            file: Uploaded video file
            title: Video title
            description: Optional video description
            tags: Optional list of tags
            category: Optional category
            
        Returns:
            Created Video object
            
        Raises:
            ValueError: If file validation fails
        """
        # Validate file type
        file_extension = file.filename.split('.')[-1].lower()
        if file_extension not in self.settings.allowed_video_formats_list:
            raise ValueError(
                f"Invalid file format. Allowed formats: {', '.join(self.settings.allowed_video_formats_list)}"
            )
        
        # Create temporary file to process video
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_file:
            try:
                # Read and save uploaded file
                content = await file.read()
                file_size = len(content)
                
                # Validate file size
                max_size = self.settings.max_upload_size_mb * 1024 * 1024
                if file_size > max_size:
                    raise ValueError(
                        f"File size exceeds maximum allowed size of {self.settings.max_upload_size_mb}MB"
                    )
                
                temp_file.write(content)
                temp_file.flush()
                temp_path = temp_file.name
                
                # Extract video metadata using FFmpeg
                video_info = self._extract_video_info(temp_path)
                
                # Generate unique object keys for S3
                video_id = uuid.uuid4()
                video_key = f"videos/{user_id}/{video_id}.{file_extension}"
                thumbnail_key = f"thumbnails/{user_id}/{video_id}.jpg"
                
                # Upload video to S3
                video_url = self.s3_service.upload_file(
                    temp_path,
                    video_key,
                    content_type=file.content_type,
                    metadata={
                        'user_id': str(user_id),
                        'original_filename': file.filename
                    }
                )
                
                # Generate and upload thumbnail
                thumbnail_path = self._generate_thumbnail(temp_path)
                thumbnail_url = self.s3_service.upload_file(
                    thumbnail_path,
                    thumbnail_key,
                    content_type='image/jpeg'
                )
                
                # Clean up temporary thumbnail
                os.unlink(thumbnail_path)
                
                # Create video record in database
                video = Video(
                    id=video_id,
                    user_id=user_id,
                    title=title,
                    description=description,
                    file_url=video_url,
                    thumbnail_url=thumbnail_url,
                    duration=video_info['duration'],
                    format=file_extension,
                    resolution=video_info['resolution'],
                    file_size=file_size,
                    tags=tags or [],
                    category=category
                )
                
                db.add(video)
                await db.commit()
                await db.refresh(video)
                
                logger.info(f"Video uploaded successfully: {video.id}")
                return video
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
    
    def _extract_video_info(self, file_path: str) -> dict:
        """Extract video metadata using FFmpeg
        
        Args:
            file_path: Path to video file
            
        Returns:
            Dictionary with duration and resolution
        """
        try:
            probe = ffmpeg.probe(file_path)
            video_stream = next(
                (stream for stream in probe['streams'] if stream['codec_type'] == 'video'),
                None
            )
            
            if not video_stream:
                raise ValueError("No video stream found in file")
            
            duration = int(float(probe['format']['duration']))
            width = video_stream['width']
            height = video_stream['height']
            resolution = f"{width}x{height}"
            
            return {
                'duration': duration,
                'resolution': resolution,
                'width': width,
                'height': height
            }
            
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error extracting video info: {e}")
            raise ValueError("Failed to process video file")
    
    def _generate_thumbnail(self, video_path: str, timestamp: float = 1.0) -> str:
        """Generate thumbnail from video
        
        Args:
            video_path: Path to video file
            timestamp: Timestamp in seconds to capture thumbnail
            
        Returns:
            Path to generated thumbnail file
        """
        try:
            # Create temporary file for thumbnail
            thumbnail_fd, thumbnail_path = tempfile.mkstemp(suffix='.jpg')
            os.close(thumbnail_fd)
            
            # Generate thumbnail using FFmpeg
            (
                ffmpeg
                .input(video_path, ss=timestamp)
                .filter('scale', 320, -1)
                .output(thumbnail_path, vframes=1, format='image2', vcodec='mjpeg')
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True, quiet=True)
            )
            
            logger.info(f"Generated thumbnail: {thumbnail_path}")
            return thumbnail_path
            
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error generating thumbnail: {e}")
            # Return a default thumbnail path or raise error
            raise ValueError("Failed to generate video thumbnail")
    
    async def get_user_videos(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Video]:
        """Get user's videos with optional filtering
        
        Args:
            db: Database session
            user_id: User ID
            tags: Filter by tags
            category: Filter by category
            search: Search in title and description
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Video objects
        """
        query = select(Video).where(Video.user_id == user_id)
        
        # Apply filters
        if tags:
            query = query.where(Video.tags.overlap(tags))
        
        if category:
            query = query.where(Video.category == category)
        
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Video.title.ilike(search_pattern),
                    Video.description.ilike(search_pattern)
                )
            )
        
        # Order by creation date (newest first)
        query = query.order_by(Video.created_at.desc())
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        videos = result.scalars().all()
        
        return list(videos)
    
    async def get_video_by_id(
        self,
        db: AsyncSession,
        video_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[Video]:
        """Get a specific video by ID
        
        Args:
            db: Database session
            video_id: Video ID
            user_id: User ID (for authorization)
            
        Returns:
            Video object or None if not found
        """
        query = select(Video).where(
            and_(
                Video.id == video_id,
                Video.user_id == user_id
            )
        )
        
        result = await db.execute(query)
        video = result.scalar_one_or_none()
        
        return video
    
    async def update_video(
        self,
        db: AsyncSession,
        video_id: uuid.UUID,
        user_id: uuid.UUID,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None
    ) -> Optional[Video]:
        """Update video metadata
        
        Args:
            db: Database session
            video_id: Video ID
            user_id: User ID (for authorization)
            title: New title
            description: New description
            tags: New tags
            category: New category
            
        Returns:
            Updated Video object or None if not found
        """
        video = await self.get_video_by_id(db, video_id, user_id)
        
        if not video:
            return None
        
        # Update fields if provided
        if title is not None:
            video.title = title
        if description is not None:
            video.description = description
        if tags is not None:
            video.tags = tags
        if category is not None:
            video.category = category
        
        video.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(video)
        
        logger.info(f"Video updated: {video.id}")
        return video
    
    async def delete_video(
        self,
        db: AsyncSession,
        video_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """Delete a video and its files from S3
        
        Args:
            db: Database session
            video_id: Video ID
            user_id: User ID (for authorization)
            
        Returns:
            True if deleted, False if not found
        """
        video = await self.get_video_by_id(db, video_id, user_id)
        
        if not video:
            return False
        
        # Extract S3 keys from URLs
        video_key = video.file_url.replace(f"s3://{self.s3_service.bucket_name}/", "")
        thumbnail_key = video.thumbnail_url.replace(f"s3://{self.s3_service.bucket_name}/", "")
        
        # Delete from S3
        try:
            self.s3_service.delete_file(video_key)
            self.s3_service.delete_file(thumbnail_key)
        except Exception as e:
            logger.error(f"Error deleting files from S3: {e}")
            # Continue with database deletion even if S3 deletion fails
        
        # Delete from database (cascade will handle related records)
        await db.delete(video)
        await db.commit()
        
        logger.info(f"Video deleted: {video_id}")
        return True
