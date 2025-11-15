"""Celery tasks for video processing and scheduling"""

import os
import tempfile
import logging
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime

from celery import Task
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.celery_app import celery_app
from src.database import get_sync_db, get_db_context
from src.models.database_models import Video, PlatformEnum, Post, PostStatusEnum, PlatformConnection, Schedule
from src.models.notification_models import NotificationTypeEnum
from src.services.video_converter import VideoConverter, VideoConversionError
from src.services.s3_service import S3Service
from src.services.notification_service import NotificationService
from src.adapters.tiktok import TikTokAdapter
from src.adapters.youtube import YouTubeAdapter
from src.adapters.instagram import InstagramAdapter
from src.adapters.facebook import FacebookAdapter
from src.adapters.base import (
    PlatformAdapter,
    PlatformAuthError,
    PlatformRateLimitError,
    PlatformAPIError,
    PostMetadata
)
from src.config import settings
from src.monitoring import track_celery_task, track_video_post, track_platform_api_call
import time

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task - database sessions are managed per-task using context managers"""
    pass


@celery_app.task(
    name="src.tasks.convert_video",
    base=DatabaseTask,
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def convert_video(
    self,
    video_id: str,
    platform: str,
    force_conversion: bool = False
) -> dict:
    """
    Convert video to platform-specific format.
    
    Args:
        video_id: UUID of the video to convert
        platform: Target platform (tiktok, youtube, instagram, facebook)
        force_conversion: Force conversion even if video meets requirements
        
    Returns:
        Dictionary with conversion results
    """
    logger.info(f"Starting video conversion: video_id={video_id}, platform={platform}")
    
    # Update task state to track progress
    self.update_state(state='PROGRESS', meta={'status': 'Initializing conversion'})
    
    try:
        with get_sync_db() as db:
            # Get video from database
            video = db.query(Video).filter(Video.id == UUID(video_id)).first()
            if not video:
                raise ValueError(f"Video not found: {video_id}")
        
        # Initialize services
        converter = VideoConverter()
        s3_service = S3Service(settings)
        platform_enum = PlatformEnum(platform)
        
        # Download original video from S3 to temp file
        self.update_state(state='PROGRESS', meta={'status': 'Downloading original video'})
        
        # Extract S3 key from URL (format: s3://bucket/key)
        original_s3_key = video.file_url.replace(f"s3://{settings.s3_bucket_name}/", "")
        
        # Create temp directory for processing
        temp_dir = tempfile.mkdtemp()
        original_path = os.path.join(temp_dir, f"original_{video_id}{Path(original_s3_key).suffix}")
        
        try:
            # Download from S3
            download_url = s3_service.generate_presigned_download_url(original_s3_key)
            import httpx
            with httpx.Client() as client:
                response = client.get(download_url)
                response.raise_for_status()
                with open(original_path, 'wb') as f:
                    f.write(response.content)
            
            logger.info(f"Downloaded video to: {original_path}")
            
            # Check if conversion is needed
            self.update_state(state='PROGRESS', meta={'status': 'Analyzing video requirements'})
            
            requirements = converter.get_conversion_requirements(original_path, platform_enum)
            
            if not force_conversion and not requirements['needs_conversion']:
                logger.info(f"Video already meets {platform} requirements, skipping conversion")
                return {
                    'success': True,
                    'converted': False,
                    'message': 'Video already meets platform requirements',
                    'converted_url': video.file_url,
                    'platform': platform
                }
            
            # Perform conversion
            self.update_state(state='PROGRESS', meta={
                'status': 'Converting video',
                'changes': requirements['changes']
            })
            
            output_filename = f"converted_{platform}_{video_id}.mp4"
            output_path = os.path.join(temp_dir, output_filename)
            
            converter.convert_for_platform(
                input_path=original_path,
                output_path=output_path,
                platform=platform_enum,
                preserve_quality=True
            )
            
            logger.info(f"Video converted successfully: {output_path}")
            
            # Upload converted video to S3
            self.update_state(state='PROGRESS', meta={'status': 'Uploading converted video'})
            
            # Generate S3 key for converted video
            user_id = str(video.user_id)
            converted_s3_key = f"videos/{user_id}/converted/{platform}/{output_filename}"
            
            converted_url = s3_service.upload_file(
                file_path=output_path,
                object_key=converted_s3_key,
                content_type='video/mp4',
                metadata={
                    'original_video_id': video_id,
                    'platform': platform,
                    'conversion_date': str(os.path.getmtime(output_path))
                }
            )
            
            logger.info(f"Converted video uploaded to S3: {converted_url}")
            
            # Get converted video metadata
            converted_metadata = converter.detect_format(output_path)
            
            return {
                'success': True,
                'converted': True,
                'message': 'Video converted successfully',
                'converted_url': converted_url,
                'converted_s3_key': converted_s3_key,
                'platform': platform,
                'changes_made': requirements['changes'],
                'metadata': {
                    'duration': converted_metadata['duration'],
                    'file_size': converted_metadata['file_size'],
                    'resolution': f"{converted_metadata['width']}x{converted_metadata['height']}",
                    'format': converted_metadata['format']
                }
            }
            
        finally:
            # Clean up temp files
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temp directory: {temp_dir}")
    
    except VideoConversionError as e:
        logger.error(f"Video conversion failed: {e}")
        # Retry on conversion errors
        raise self.retry(exc=e, countdown=60)
    
    except Exception as e:
        logger.error(f"Unexpected error during video conversion: {e}", exc_info=True)
        return {
            'success': False,
            'converted': False,
            'message': f'Conversion failed: {str(e)}',
            'error': str(e),
            'platform': platform
        }


@celery_app.task(
    name="src.tasks.post_video",
    base=DatabaseTask,
    bind=True,
    max_retries=3,
    autoretry_for=(PlatformRateLimitError, PlatformAPIError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
def post_video(self, post_id: str) -> dict:
    """
    Post video to platform.
    
    This task handles uploading and posting a video to a specific platform.
    It includes retry logic with exponential backoff for transient errors.
    
    Args:
        post_id: UUID of the post to execute
        
    Returns:
        Dictionary with posting results
    """
    logger.info(f"Starting video post: post_id={post_id}")
    
    # Update task state
    self.update_state(state='PROGRESS', meta={'status': 'Initializing post'})
    
    try:
        with get_sync_db() as db:
            # Get post from database
            post = db.query(Post).filter(Post.id == UUID(post_id)).first()
            if not post:
                raise ValueError(f"Post not found: {post_id}")
            
            # Update status to processing
            post.status = PostStatusEnum.PROCESSING
            db.commit()
            
            # Get video
            video = db.query(Video).filter(Video.id == post.video_id).first()
            if not video:
                raise ValueError(f"Video not found: {post.video_id}")
            
            # Get platform authentication
            platform_auth = db.query(PlatformConnection).filter(
                PlatformConnection.user_id == post.user_id,
                PlatformConnection.platform == post.platform,
                PlatformConnection.is_active == True
            ).first()
            
            if not platform_auth:
                raise PlatformAuthError(
                    f"No active authentication found for {post.platform.value}",
                    platform=post.platform.value
                )
        
        # Check if token is expired
        if platform_auth.token_expires_at and platform_auth.token_expires_at <= datetime.utcnow():
            raise PlatformAuthError(
                f"Authentication token expired for {post.platform.value}",
                platform=post.platform.value
            )
        
        # Get platform adapter
        adapter = _get_platform_adapter(post.platform.value)
        if not adapter:
            raise ValueError(f"Unsupported platform: {post.platform.value}")
        
        # Get access token (PlatformConnection stores it directly, not encrypted)
        access_token = platform_auth.access_token
        
        # Download video from S3 to temp file
        self.update_state(state='PROGRESS', meta={'status': 'Downloading video'})
        
        s3_service = S3Service(settings)
        video_s3_key = video.file_url.replace(f"s3://{settings.s3_bucket_name}/", "")
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        video_path = os.path.join(temp_dir, f"video_{post_id}{Path(video_s3_key).suffix}")
        
        try:
            # Download from S3
            download_url = s3_service.generate_presigned_download_url(video_s3_key)
            import httpx
            with httpx.Client() as client:
                response = client.get(download_url)
                response.raise_for_status()
                with open(video_path, 'wb') as f:
                    f.write(response.content)
            
            logger.info(f"Downloaded video to: {video_path}")
            
            # Prepare post metadata
            self.update_state(state='PROGRESS', meta={'status': 'Uploading to platform'})
            
            metadata = PostMetadata(
                caption=post.caption,
                hashtags=post.hashtags,
                privacy_level="public",  # Default, can be customized
                disable_comments=False,
                disable_duet=False,
                disable_stitch=False
            )
            
            # Upload video to platform
            import asyncio
            start_time = time.time()
            try:
                platform_post = asyncio.run(
                    adapter.upload_video(
                        video_path=video_path,
                        metadata=metadata,
                        access_token=access_token
                    )
                )
                duration = time.time() - start_time
                track_platform_api_call(post.platform.value, "upload", "success", duration)
            except Exception as e:
                duration = time.time() - start_time
                track_platform_api_call(post.platform.value, "upload", "failed", duration)
                raise
            
            # Update post with platform response
            with get_sync_db() as db:
                post = db.query(Post).filter(Post.id == UUID(post_id)).first()
                if post:
                    post.status = PostStatusEnum.POSTED
                    post.platform_post_id = platform_post.platform_post_id
                    post.platform_url = platform_post.platform_url
                    post.posted_at = datetime.utcnow()
                    post.error_message = None
                    db.commit()
                    
                    # Send success notification
                    _send_post_notification(
                        db=db,
                        user_id=post.user_id,
                        video_id=post.video_id,
                        post_id=post.id,
                        platform=post.platform.value,
                        success=True,
                        platform_url=platform_post.platform_url
                    )
                    
                    # Track metrics
                    track_video_post(post.platform.value, "success")
                    track_celery_task("post_video", "success")
            
            logger.info(
                f"Video posted successfully: post_id={post_id}, "
                f"platform_post_id={platform_post.platform_post_id}"
            )
            
            return {
                'success': True,
                'post_id': post_id,
                'platform': post.platform.value,
                'platform_post_id': platform_post.platform_post_id,
                'platform_url': platform_post.platform_url,
                'status': platform_post.status
            }
            
        finally:
            # Clean up temp files
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temp directory: {temp_dir}")
    
    except PlatformAuthError as e:
        logger.error(f"Authentication error posting video: {e}")
        
        # Update post status to failed (don't retry auth errors)
        with get_sync_db() as db:
            post = db.query(Post).filter(Post.id == UUID(post_id)).first()
            if post:
                post.status = PostStatusEnum.FAILED
                post.error_message = str(e)
                db.commit()
                
                # Send failure notification
                _send_post_notification(
                    db=db,
                    user_id=post.user_id,
                    video_id=post.video_id,
                    post_id=post.id,
                    platform=post.platform.value,
                    success=False,
                    error_message=str(e)
                )
        
        return {
            'success': False,
            'post_id': post_id,
            'error': 'authentication_error',
            'message': str(e)
        }
    
    except PlatformRateLimitError as e:
        logger.warning(f"Rate limit hit for post {post_id}: {e}")
        
        # Update retry count
        with get_sync_db() as db:
            post = db.query(Post).filter(Post.id == UUID(post_id)).first()
            if post:
                post.retry_count += 1
                post.error_message = f"Rate limited. Retry after {e.retry_after} seconds."
                db.commit()
        
        # Retry with delay
        raise self.retry(exc=e, countdown=e.retry_after or 60)
    
    except PlatformAPIError as e:
        logger.error(f"Platform API error posting video: {e}")
        
        # Update retry count
        with get_sync_db() as db:
            post = db.query(Post).filter(Post.id == UUID(post_id)).first()
            if post:
                post.retry_count += 1
                post.error_message = str(e)
                
                # Check if max retries reached
                if post.retry_count >= 3:
                    post.status = PostStatusEnum.FAILED
                    logger.error(f"Max retries reached for post {post_id}")
                    
                    # Send failure notification after all retries exhausted
                    _send_post_notification(
                        db=db,
                        user_id=post.user_id,
                        video_id=post.video_id,
                        post_id=post.id,
                        platform=post.platform.value,
                        success=False,
                        error_message=str(e)
                    )
                
                db.commit()
                
                # Retry if not max retries
                if post.retry_count < 3:
                    raise self.retry(exc=e, countdown=60 * (2 ** post.retry_count))
        
        return {
            'success': False,
            'post_id': post_id,
            'error': 'platform_api_error',
            'message': str(e)
        }
    
    except Exception as e:
        logger.error(f"Unexpected error posting video: {e}", exc_info=True)
        
        # Update post status to failed
        with get_sync_db() as db:
            post = db.query(Post).filter(Post.id == UUID(post_id)).first()
            if post:
                post.status = PostStatusEnum.FAILED
                post.error_message = f"Unexpected error: {str(e)}"
                db.commit()
                
                # Send failure notification
                _send_post_notification(
                    db=db,
                    user_id=post.user_id,
                    video_id=post.video_id,
                    post_id=post.id,
                    platform=post.platform.value,
                    success=False,
                    error_message=f"Unexpected error: {str(e)}"
                )
        
        return {
            'success': False,
            'post_id': post_id,
            'error': 'unexpected_error',
            'message': str(e)
        }


def _get_platform_adapter(platform: str) -> Optional[PlatformAdapter]:
    """Get platform adapter instance
    
    Args:
        platform: Platform name (tiktok, youtube, instagram, facebook, twitter)
        
    Returns:
        Platform adapter instance or None
    """
    # Convert to lowercase for case-insensitive matching
    platform_lower = platform.lower()
    
    if platform_lower == "tiktok":
        if settings.tiktok_client_id and settings.tiktok_client_secret:
            return TikTokAdapter(
                client_id=settings.tiktok_client_id,
                client_secret=settings.tiktok_client_secret,
                redirect_uri=settings.tiktok_redirect_uri
            )
    elif platform_lower == "youtube":
        if settings.youtube_client_id and settings.youtube_client_secret:
            return YouTubeAdapter(
                client_id=settings.youtube_client_id,
                client_secret=settings.youtube_client_secret,
                redirect_uri=settings.youtube_redirect_uri
            )
    elif platform_lower == "instagram":
        if settings.instagram_client_id and settings.instagram_client_secret:
            return InstagramAdapter(
                client_id=settings.instagram_client_id,
                client_secret=settings.instagram_client_secret,
                redirect_uri=settings.instagram_redirect_uri
            )
    elif platform_lower == "facebook":
        if settings.facebook_client_id and settings.facebook_client_secret:
            return FacebookAdapter(
                client_id=settings.facebook_client_id,
                client_secret=settings.facebook_client_secret,
                redirect_uri=settings.facebook_redirect_uri
            )
    elif platform_lower == "twitter":
        from src.adapters.twitter import TwitterAdapter
        if settings.twitter_client_id and settings.twitter_client_secret:
            return TwitterAdapter(
                client_id=settings.twitter_client_id,
                client_secret=settings.twitter_client_secret,
                redirect_uri=settings.twitter_redirect_uri
            )
    
    return None


@celery_app.task(
    name="src.tasks.check_scheduled_posts",
    base=DatabaseTask,
    bind=True
)
def check_scheduled_posts(self):
    """
    Check for scheduled posts that need to be executed.
    
    This task runs every minute via Celery beat and:
    1. Finds schedules due within the next 60 seconds
    2. Creates multi-posts for each due schedule
    3. Queues post_video tasks for each platform
    4. Updates recurring schedules to their next occurrence
    """
    logger.info("Checking for scheduled posts...")
    
    try:
        from src.services.scheduler_service import SchedulerService
        from src.adapters.tiktok import TikTokAdapter
        
        scheduler_service = SchedulerService(settings)
        
        # Initialize platform adapters
        platform_adapters = {}
        if settings.tiktok_client_id and settings.tiktok_client_secret:
            platform_adapters["tiktok"] = TikTokAdapter(
                client_id=settings.tiktok_client_id,
                client_secret=settings.tiktok_client_secret,
                redirect_uri=settings.tiktok_redirect_uri
            )
        
        if settings.youtube_client_id and settings.youtube_client_secret:
            from src.adapters.youtube import YouTubeAdapter
            platform_adapters["youtube"] = YouTubeAdapter(
                client_id=settings.youtube_client_id,
                client_secret=settings.youtube_client_secret,
                redirect_uri=settings.youtube_redirect_uri
            )
        
        if settings.instagram_client_id and settings.instagram_client_secret:
            from src.adapters.instagram import InstagramAdapter
            platform_adapters["instagram"] = InstagramAdapter(
                client_id=settings.instagram_client_id,
                client_secret=settings.instagram_client_secret,
                redirect_uri=settings.instagram_redirect_uri
            )
        
        if settings.facebook_client_id and settings.facebook_client_secret:
            from src.adapters.facebook import FacebookAdapter
            platform_adapters["facebook"] = FacebookAdapter(
                client_id=settings.facebook_client_id,
                client_secret=settings.facebook_client_secret,
                redirect_uri=settings.facebook_redirect_uri
            )
        
        if settings.twitter_client_id and settings.twitter_client_secret:
            from src.adapters.twitter import TwitterAdapter
            platform_adapters["twitter"] = TwitterAdapter(
                client_id=settings.twitter_client_id,
                client_secret=settings.twitter_client_secret,
                redirect_uri=settings.twitter_redirect_uri
            )
        
        # Get schedules due within the next 60 seconds using sync database
        from datetime import datetime, timedelta
        with get_sync_db() as db:
            now = datetime.utcnow()
            window_end = now + timedelta(seconds=60)
            
            schedules = db.query(Schedule).filter(
                Schedule.is_active == True,
                Schedule.scheduled_at <= window_end,
                Schedule.scheduled_at > now - timedelta(seconds=60)
            ).order_by(Schedule.scheduled_at).all()
            
        logger.info(f"Found {len(schedules)} schedules due for execution")
        
        for schedule in schedules:
            try:
                logger.info(
                    f"Processing schedule {schedule.id} for video {schedule.video_id} "
                    f"scheduled at {schedule.scheduled_at}"
                )
                
                # Create posts for each platform using sync database
                with get_sync_db() as db:
                    # Get video
                    video = db.query(Video).filter(Video.id == schedule.video_id).first()
                    if not video:
                        logger.error(f"Video {schedule.video_id} not found for schedule {schedule.id}")
                        continue
                    
                    # Create a MultiPost
                    from src.models.database_models import MultiPost
                    multi_post = MultiPost(
                        id=uuid4(),
                        user_id=schedule.user_id,
                        video_id=schedule.video_id
                    )
                    db.add(multi_post)
                    db.flush()
                    
                    # Create Post records for each platform
                    for platform_name in [p.value for p in schedule.platforms]:
                        platform_enum = PlatformEnum(platform_name)
                        config = schedule.post_config.get(platform_name, {})
                        
                        # Handle caption rotation for recurring schedules
                        caption = config.get("caption", "")
                        caption_variations = config.get("caption_variations", [])
                        
                        if schedule.is_recurring and caption_variations:
                            # Use caption variation at the current index
                            actual_index = schedule.caption_rotation_index % len(caption_variations)
                            caption = caption_variations[actual_index]
                            logger.info(
                                f"Using caption variation {actual_index + 1}/{len(caption_variations)} "
                                f"for platform {platform_name} in schedule {schedule.id}"
                            )
                        
                        post = Post(
                            id=uuid4(),
                            user_id=schedule.user_id,
                            video_id=schedule.video_id,
                            multi_post_id=multi_post.id,
                            platform=platform_enum,
                            status=PostStatusEnum.PENDING,
                            caption=caption,
                            hashtags=config.get("hashtags", []),
                            scheduled_at=None,
                            retry_count=0
                        )
                        db.add(post)
                        db.flush()
                        
                        # Queue post_video task
                        post_video.apply_async(
                            args=[str(post.id)],
                            countdown=0
                        )
                        logger.info(f"Queued post_video task for post {post.id}")
                    
                    # Handle recurring schedules
                    if schedule.is_recurring and schedule.recurrence_pattern:
                        # Calculate next occurrence
                        next_occurrence = scheduler_service.calculate_next_occurrence(
                            recurrence_pattern=schedule.recurrence_pattern,
                            from_time=schedule.scheduled_at
                        )
                        
                        # Update schedule to next occurrence and increment caption rotation index
                        schedule_to_update = db.query(Schedule).filter(Schedule.id == schedule.id).first()
                        if schedule_to_update:
                            schedule_to_update.scheduled_at = next_occurrence
                            schedule_to_update.caption_rotation_index += 1
                            db.commit()
                        
                        logger.info(
                            f"Updated recurring schedule {schedule.id} to next occurrence: "
                            f"{next_occurrence.isoformat()}, caption_index: {schedule_to_update.caption_rotation_index}"
                        )
                    else:
                        # Mark one-time schedule as inactive
                        schedule_to_update = db.query(Schedule).filter(Schedule.id == schedule.id).first()
                        if schedule_to_update:
                            schedule_to_update.is_active = False
                            db.commit()
                        
                        logger.info(f"Marked one-time schedule {schedule.id} as inactive")
            
            except Exception as e:
                logger.error(
                    f"Error processing schedule {schedule.id}: {e}",
                    exc_info=True
                )
                # Continue processing other schedules
                continue
        
        logger.info("Finished checking scheduled posts")
        
        return {
            'success': True,
            'message': 'Scheduled posts checked successfully'
        }
    
    except Exception as e:
        logger.error(f"Error checking scheduled posts: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


@celery_app.task(
    name="src.tasks.repost_video",
    base=DatabaseTask,
    bind=True,
    max_retries=3,
    autoretry_for=(PlatformRateLimitError, PlatformAPIError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
def repost_video(self, schedule_id: str, caption_index: int = 0) -> dict:
    """
    Repost video from a recurring schedule with caption rotation.
    
    This task handles reposting a video with caption variations for recurring schedules.
    It cycles through different caption variations on each execution.
    
    Args:
        schedule_id: UUID of the recurring schedule
        caption_index: Index of the caption variation to use
        
    Returns:
        Dictionary with repost results
    """
    logger.info(f"Starting video repost: schedule_id={schedule_id}, caption_index={caption_index}")
    
    try:
        with get_sync_db() as db:
            # Get schedule from database
            from src.models.database_models import Schedule
            schedule = db.query(Schedule).filter(Schedule.id == UUID(schedule_id)).first()
            if not schedule:
                raise ValueError(f"Schedule not found: {schedule_id}")
            
            # Verify it's a recurring schedule
            if not schedule.is_recurring:
                raise ValueError(f"Schedule {schedule_id} is not a recurring schedule")
            
            # Get video
            video = db.query(Video).filter(Video.id == schedule.video_id).first()
            if not video:
                raise ValueError(f"Video not found: {schedule.video_id}")
            
            # Create a MultiPost
            from src.models.database_models import MultiPost
            multi_post = MultiPost(
                id=uuid4(),
                user_id=schedule.user_id,
                video_id=schedule.video_id
            )
            db.add(multi_post)
            db.flush()
            
            # Create Post records for each platform with caption rotation
            posts_created = []
            for platform_name in [p.value for p in schedule.platforms]:
                platform_enum = PlatformEnum(platform_name)
                config = schedule.post_config.get(platform_name, {})
                
                # Handle caption rotation
                caption = config.get("caption", "")
                caption_variations = config.get("caption_variations", [])
                
                if caption_variations:
                    # Use caption variation at the specified index (cycle through)
                    actual_index = caption_index % len(caption_variations)
                    caption = caption_variations[actual_index]
                    logger.info(
                        f"Using caption variation {actual_index + 1}/{len(caption_variations)} "
                        f"for platform {platform_name}"
                    )
                
                post = Post(
                    id=uuid4(),
                    user_id=schedule.user_id,
                    video_id=schedule.video_id,
                    multi_post_id=multi_post.id,
                    platform=platform_enum,
                    status=PostStatusEnum.PENDING,
                    caption=caption,
                    hashtags=config.get("hashtags", []),
                    scheduled_at=None,
                    retry_count=0
                )
                db.add(post)
                db.flush()
                posts_created.append(post.id)
                
                # Queue post_video task
                post_video.apply_async(
                    args=[str(post.id)],
                    countdown=0
                )
                logger.info(f"Queued post_video task for repost {post.id}")
            
            db.commit()
            
            logger.info(
                f"Created repost with {len(posts_created)} posts from schedule {schedule_id}"
            )
            
            return {
                'success': True,
                'schedule_id': schedule_id,
                'multi_post_id': str(multi_post.id),
                'posts_created': [str(p) for p in posts_created],
                'caption_index': caption_index
            }
    
    except Exception as e:
        logger.error(f"Error reposting video: {e}", exc_info=True)
        return {
            'success': False,
            'schedule_id': schedule_id,
            'error': str(e)
        }


@celery_app.task(
    name="src.tasks.sync_analytics",
    base=DatabaseTask,
    bind=True
)
def sync_analytics(self):
    """
    Sync analytics from all platforms for all posted videos.
    
    This task runs periodically (every 6 hours) to fetch updated metrics
    from each platform and store them in the VideoAnalytics table.
    """
    logger.info("Starting analytics sync...")
    
    try:
        from src.models.database_models import VideoAnalytics
        from src.adapters.youtube import YouTubeAdapter
        from src.adapters.instagram import InstagramAdapter
        from src.adapters.facebook import FacebookAdapter
        
        # Initialize platform adapters
        platform_adapters = {}
        
        if settings.tiktok_client_id and settings.tiktok_client_secret:
            platform_adapters["tiktok"] = TikTokAdapter(
                client_id=settings.tiktok_client_id,
                client_secret=settings.tiktok_client_secret,
                redirect_uri=settings.tiktok_redirect_uri
            )
        
        if settings.youtube_client_id and settings.youtube_client_secret:
            platform_adapters["youtube"] = YouTubeAdapter(
                client_id=settings.youtube_client_id,
                client_secret=settings.youtube_client_secret,
                redirect_uri=settings.youtube_redirect_uri
            )
        
        if settings.instagram_client_id and settings.instagram_client_secret:
            platform_adapters["instagram"] = InstagramAdapter(
                client_id=settings.instagram_client_id,
                client_secret=settings.instagram_client_secret,
                redirect_uri=settings.instagram_redirect_uri
            )
        
        if settings.facebook_client_id and settings.facebook_client_secret:
            platform_adapters["facebook"] = FacebookAdapter(
                client_id=settings.facebook_client_id,
                client_secret=settings.facebook_client_secret,
                redirect_uri=settings.facebook_redirect_uri
            )
        
        if settings.twitter_client_id and settings.twitter_client_secret:
            from src.adapters.twitter import TwitterAdapter
            platform_adapters["twitter"] = TwitterAdapter(
                client_id=settings.twitter_client_id,
                client_secret=settings.twitter_client_secret,
                redirect_uri=settings.twitter_redirect_uri
            )
        
        synced_count = 0
        error_count = 0
        
        with get_sync_db() as db:
            # Get all posted videos with platform post IDs
            posts = db.query(Post).filter(
                Post.status == PostStatusEnum.POSTED,
                Post.platform_post_id.isnot(None)
            ).all()
            
            logger.info(f"Found {len(posts)} posted videos to sync analytics for")
            
            for post in posts:
                try:
                    platform_name = post.platform.value
                    
                    # Skip if adapter not configured
                    if platform_name not in platform_adapters:
                        logger.debug(f"Skipping {platform_name} - adapter not configured")
                        continue
                    
                    # Get platform authentication
                    platform_auth = db.query(PlatformAuth).filter(
                        PlatformAuth.user_id == post.user_id,
                        PlatformAuth.platform == post.platform,
                        PlatformAuth.is_active == True
                    ).first()
                    
                    if not platform_auth:
                        logger.warning(
                            f"No active auth for user {post.user_id} on {platform_name}, "
                            f"skipping post {post.id}"
                        )
                        continue
                    
                    # Check if token is expired
                    if platform_auth.token_expires_at <= datetime.utcnow():
                        logger.warning(
                            f"Token expired for user {post.user_id} on {platform_name}, "
                            f"skipping post {post.id}"
                        )
                        continue
                    
                    # Get access token
                    access_token = platform_auth.get_access_token()
                    
                    # Fetch analytics from platform (convert to lowercase for lookup)
                    adapter = platform_adapters[platform_name.lower()]
                    
                    import asyncio
                    analytics = asyncio.run(
                        adapter.get_video_analytics(
                            platform_post_id=post.platform_post_id,
                            access_token=access_token
                        )
                    )
                    
                    # Check if analytics record exists
                    existing_analytics = db.query(VideoAnalytics).filter(
                        VideoAnalytics.video_id == post.video_id,
                        VideoAnalytics.platform == post.platform,
                        VideoAnalytics.platform_post_id == post.platform_post_id
                    ).first()
                    
                    if existing_analytics:
                        # Update existing record
                        existing_analytics.views = analytics.views
                        existing_analytics.likes = analytics.likes
                        existing_analytics.comments = analytics.comments
                        existing_analytics.shares = analytics.shares
                        existing_analytics.synced_at = datetime.utcnow()
                    else:
                        # Create new record
                        new_analytics = VideoAnalytics(
                            id=uuid4(),
                            video_id=post.video_id,
                            platform=post.platform,
                            platform_post_id=post.platform_post_id,
                            views=analytics.views,
                            likes=analytics.likes,
                            comments=analytics.comments,
                            shares=analytics.shares,
                            synced_at=datetime.utcnow()
                        )
                        db.add(new_analytics)
                    
                    db.commit()
                    synced_count += 1
                    
                    logger.debug(
                        f"Synced analytics for post {post.id} ({platform_name}): "
                        f"views={analytics.views}, likes={analytics.likes}, "
                        f"comments={analytics.comments}, shares={analytics.shares}"
                    )
                    
                except PlatformAuthError as e:
                    logger.error(f"Auth error syncing analytics for post {post.id}: {e}")
                    error_count += 1
                    continue
                
                except PlatformAPIError as e:
                    logger.error(f"API error syncing analytics for post {post.id}: {e}")
                    error_count += 1
                    continue
                
                except Exception as e:
                    logger.error(
                        f"Unexpected error syncing analytics for post {post.id}: {e}",
                        exc_info=True
                    )
                    error_count += 1
                    continue
        
        logger.info(
            f"Analytics sync completed: {synced_count} synced, {error_count} errors"
        )
        
        return {
            'success': True,
            'synced_count': synced_count,
            'error_count': error_count,
            'message': f'Synced analytics for {synced_count} posts'
        }
    
    except Exception as e:
        logger.error(f"Error in analytics sync task: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


@celery_app.task(name="src.tasks.refresh_expiring_tokens")
def refresh_expiring_tokens():
    """Refresh platform tokens that are about to expire"""
    # Implementation will be added in later tasks
    pass


def _send_post_notification(
    db: Session,
    user_id: UUID,
    video_id: UUID,
    post_id: UUID,
    platform: str,
    success: bool,
    platform_url: Optional[str] = None,
    error_message: Optional[str] = None
) -> None:
    """
    Send notification for post completion (success or failure).
    
    This function creates in-app notifications and queues email notifications
    with batching support.
    
    Args:
        db: Database session
        user_id: User ID
        video_id: Video ID
        post_id: Post ID
        platform: Platform name
        success: Whether the post was successful
        platform_url: URL of the posted video (for success)
        error_message: Error message (for failure)
    """
    try:
        # Get video title for notification
        video = db.query(Video).filter(Video.id == video_id).first()
        video_title = video.title if video else "your video"
        
        # Create notification service (using sync session)
        import asyncio
        
        async def create_and_batch_notification():
            # We need to use async context for notification service
            async with get_db_context() as async_db:
                notification_service = NotificationService(async_db)
                
                if success:
                    # Success notification
                    title = f"Video posted to {platform.capitalize()}"
                    message = f'"{video_title}" was successfully posted to {platform.capitalize()}.'
                    if platform_url:
                        message += f" View it at: {platform_url}"
                    
                    notification_type = NotificationTypeEnum.POST_SUCCESS
                else:
                    # Failure notification
                    title = f"Failed to post to {platform.capitalize()}"
                    message = f'"{video_title}" could not be posted to {platform.capitalize()}.'
                    if error_message:
                        message += f" Error: {error_message}"
                    
                    notification_type = NotificationTypeEnum.POST_FAILURE
                
                # Create in-app notification
                notification = await notification_service.create_notification(
                    user_id=user_id,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    metadata={
                        'video_id': str(video_id),
                        'post_id': str(post_id),
                        'platform': platform,
                        'platform_url': platform_url,
                        'error_message': error_message,
                    }
                )
                
                # Add to batch for email notification
                batch = await notification_service.get_or_create_batch(
                    user_id=user_id,
                    notification_type=notification_type
                )
                
                await notification_service.add_to_batch(
                    batch=batch,
                    notification_id=notification.id
                )
                
                logger.info(
                    f"Created notification {notification.id} for post {post_id} "
                    f"(success={success})"
                )
        
        # Run async notification creation
        asyncio.run(create_and_batch_notification())
        
        # Queue task to send batched notifications (after batching window)
        send_batched_notifications.apply_async(
            args=[str(user_id), NotificationTypeEnum.POST_SUCCESS.value if success else NotificationTypeEnum.POST_FAILURE.value],
            countdown=NotificationService.BATCH_WINDOW_MINUTES * 60 + 10  # Wait for batch window + 10 seconds
        )
        
    except Exception as e:
        logger.error(f"Error sending notification for post {post_id}: {e}", exc_info=True)
        # Don't fail the task if notification fails


@celery_app.task(
    name="src.tasks.send_batched_notifications",
    base=DatabaseTask,
    bind=True
)
def send_batched_notifications(self, user_id: str, notification_type: str) -> dict:
    """
    Send batched notifications via email.
    
    This task is queued after the batching window to send accumulated
    notifications as a single email.
    
    Args:
        user_id: User ID
        notification_type: Type of notification (post_success, post_failure, etc.)
        
    Returns:
        Dictionary with send results
    """
    logger.info(f"Sending batched notifications for user {user_id}, type {notification_type}")
    
    try:
        import asyncio
        
        async def send_batch():
            async with get_db_context() as db:
                notification_service = NotificationService(db)
                
                success = await notification_service.send_batched_notifications(
                    user_id=UUID(user_id),
                    notification_type=NotificationTypeEnum(notification_type)
                )
                
                return success
        
        success = asyncio.run(send_batch())
        
        return {
            'success': success,
            'user_id': user_id,
            'notification_type': notification_type
        }
    
    except Exception as e:
        logger.error(f"Error sending batched notifications: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }
