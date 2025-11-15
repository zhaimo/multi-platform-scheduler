"""
TikTok platform adapter implementation.
"""
import httpx
import os
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

from .base import (
    PlatformAdapter,
    PlatformAuthError,
    PlatformRateLimitError,
    PlatformAPIError,
    PlatformTokens,
    PostMetadata,
    PlatformPost,
    VideoAnalytics,
    ValidationResult,
    PlatformLimits,
    Video,
)


class TikTokAdapter(PlatformAdapter):
    """
    TikTok platform adapter using TikTok Content Posting API.
    Implements OAuth 2.0 flow and video upload functionality.
    """
    
    # TikTok API endpoints
    AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
    TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
    VIDEO_UPLOAD_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
    VIDEO_STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
    ANALYTICS_URL = "https://open.tiktokapis.com/v2/research/video/query/"
    
    # TikTok limits
    MAX_CAPTION_LENGTH = 2200
    MAX_HASHTAGS = 30
    MAX_VIDEO_DURATION = 600  # 10 minutes
    MIN_VIDEO_DURATION = 3
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
    SUPPORTED_FORMATS = ["mp4", "mov", "webm"]
    SUPPORTED_RESOLUTIONS = ["720p", "1080p", "2K", "4K"]
    ASPECT_RATIOS = ["9:16", "1:1", "16:9"]
    
    def _get_platform_name(self) -> str:
        """Return platform name."""
        return "tiktok"
    
    def get_authorization_url(self, state: str, scope: Optional[str] = None) -> str:
        """
        Generate TikTok OAuth authorization URL.
        
        Args:
            state: State parameter for CSRF protection
            scope: OAuth scopes (default: video.upload, user.info.basic)
            
        Returns:
            Authorization URL
        """
        if scope is None:
            scope = "video.upload,user.info.basic"
        
        params = {
            "client_key": self.client_id,
            "response_type": "code",
            "scope": scope,
            "redirect_uri": self.redirect_uri,
            "state": state,
        }
        
        return f"{self.AUTH_URL}?{urlencode(params)}"
    
    async def authenticate(self, auth_code: str) -> PlatformTokens:
        """
        Exchange authorization code for access token.
        
        Args:
            auth_code: Authorization code from OAuth callback
            
        Returns:
            PlatformTokens with access and refresh tokens
            
        Raises:
            PlatformAuthError: If authentication fails
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.TOKEN_URL,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={
                        "client_key": self.client_id,
                        "client_secret": self.client_secret,
                        "code": auth_code,
                        "grant_type": "authorization_code",
                        "redirect_uri": self.redirect_uri,
                    },
                    timeout=30.0,
                )
                
                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    raise PlatformAuthError(
                        f"TikTok authentication failed: {error_data.get('error_description', 'Unknown error')}",
                        platform=self.platform_name,
                        details=error_data,
                    )
                
                data = response.json()
                
                # TikTok returns expires_in (seconds)
                expires_in = data.get("expires_in", 86400)  # default 24 hours
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                return PlatformTokens(
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token"),
                    expires_at=expires_at,
                    platform_user_id=data.get("open_id", ""),
                    scope=data.get("scope"),
                )
                
            except httpx.RequestError as e:
                raise PlatformAuthError(
                    f"Network error during TikTok authentication: {str(e)}",
                    platform=self.platform_name,
                )
    
    async def refresh_token(self, refresh_token: str) -> PlatformTokens:
        """
        Refresh TikTok access token.
        
        Args:
            refresh_token: Refresh token from previous authentication
            
        Returns:
            PlatformTokens with new access token
            
        Raises:
            PlatformAuthError: If token refresh fails
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.TOKEN_URL,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={
                        "client_key": self.client_id,
                        "client_secret": self.client_secret,
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                    },
                    timeout=30.0,
                )
                
                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    raise PlatformAuthError(
                        f"TikTok token refresh failed: {error_data.get('error_description', 'Unknown error')}",
                        platform=self.platform_name,
                        details=error_data,
                    )
                
                data = response.json()
                
                expires_in = data.get("expires_in", 86400)
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                return PlatformTokens(
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token", refresh_token),
                    expires_at=expires_at,
                    platform_user_id=data.get("open_id", ""),
                    scope=data.get("scope"),
                )
                
            except httpx.RequestError as e:
                raise PlatformAuthError(
                    f"Network error during TikTok token refresh: {str(e)}",
                    platform=self.platform_name,
                )
    
    async def upload_video(
        self,
        video_path: str,
        metadata: PostMetadata,
        access_token: str
    ) -> PlatformPost:
        """
        Upload and post video to TikTok.
        
        TikTok uses a two-step process:
        1. Initialize upload and get upload URL
        2. Upload video file to the URL
        
        Args:
            video_path: Local path to video file
            metadata: Post metadata (caption, hashtags, etc.)
            access_token: Valid access token
            
        Returns:
            PlatformPost with post ID and status
            
        Raises:
            PlatformAuthError: If access token is invalid
            PlatformRateLimitError: If rate limit is exceeded
            PlatformAPIError: If upload fails
        """
        async with httpx.AsyncClient() as client:
            try:
                # Step 1: Initialize upload
                file_size = os.path.getsize(video_path)
                
                init_payload = {
                    "post_info": {
                        "title": metadata.caption,
                        "privacy_level": metadata.privacy_level.upper(),
                        "disable_comment": metadata.disable_comments,
                        "disable_duet": metadata.disable_duet,
                        "disable_stitch": metadata.disable_stitch,
                    },
                    "source_info": {
                        "source": "FILE_UPLOAD",
                        "video_size": file_size,
                    }
                }
                
                response = await client.post(
                    self.VIDEO_UPLOAD_URL,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json; charset=UTF-8",
                    },
                    json=init_payload,
                    timeout=30.0,
                )
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    raise PlatformRateLimitError(
                        "TikTok rate limit exceeded",
                        platform=self.platform_name,
                        retry_after=retry_after,
                    )
                
                # Handle auth errors
                if response.status_code == 401:
                    raise PlatformAuthError(
                        "TikTok access token is invalid or expired",
                        platform=self.platform_name,
                    )
                
                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    raise PlatformAPIError(
                        f"TikTok upload initialization failed: {error_data.get('error', {}).get('message', 'Unknown error')}",
                        platform=self.platform_name,
                        status_code=response.status_code,
                        details=error_data,
                    )
                
                init_data = response.json()
                upload_url = init_data["data"]["upload_url"]
                publish_id = init_data["data"]["publish_id"]
                
                # Step 2: Upload video file
                with open(video_path, "rb") as video_file:
                    upload_response = await client.put(
                        upload_url,
                        headers={
                            "Content-Type": "video/mp4",
                        },
                        content=video_file.read(),
                        timeout=300.0,  # 5 minutes for large files
                    )
                    
                    if upload_response.status_code not in (200, 201):
                        raise PlatformAPIError(
                            f"TikTok video upload failed with status {upload_response.status_code}",
                            platform=self.platform_name,
                            status_code=upload_response.status_code,
                        )
                
                return PlatformPost(
                    platform_post_id=publish_id,
                    platform_url=None,  # TikTok doesn't provide URL immediately
                    posted_at=datetime.utcnow(),
                    status="processing",  # TikTok processes videos asynchronously
                    additional_data={"publish_id": publish_id},
                )
                
            except httpx.RequestError as e:
                raise PlatformAPIError(
                    f"Network error during TikTok upload: {str(e)}",
                    platform=self.platform_name,
                )
    
    async def get_video_analytics(
        self,
        platform_post_id: str,
        access_token: str
    ) -> VideoAnalytics:
        """
        Fetch video analytics from TikTok.
        
        Note: TikTok Research API has limited access. This is a basic implementation.
        
        Args:
            platform_post_id: TikTok video ID
            access_token: Valid access token
            
        Returns:
            VideoAnalytics with available metrics
            
        Raises:
            PlatformAuthError: If access token is invalid
            PlatformAPIError: If API request fails
        """
        # Note: TikTok's analytics API requires special permissions
        # This is a placeholder implementation
        return VideoAnalytics(
            views=0,
            likes=0,
            comments=0,
            shares=0,
            additional_metrics={"note": "TikTok analytics require special API access"},
        )
    
    def validate_video(self, video: Video) -> ValidationResult:
        """
        Validate video against TikTok requirements.
        
        Args:
            video: Video information to validate
            
        Returns:
            ValidationResult with validation status and errors
        """
        errors = []
        warnings = []
        
        # Check format
        if video.format.lower() not in self.SUPPORTED_FORMATS:
            errors.append(
                f"Unsupported format '{video.format}'. "
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            )
        
        # Check duration
        if video.duration < self.MIN_VIDEO_DURATION:
            errors.append(
                f"Video too short ({video.duration}s). "
                f"Minimum duration: {self.MIN_VIDEO_DURATION}s"
            )
        
        if video.duration > self.MAX_VIDEO_DURATION:
            errors.append(
                f"Video too long ({video.duration}s). "
                f"Maximum duration: {self.MAX_VIDEO_DURATION}s"
            )
        
        # Check file size
        if video.file_size > self.MAX_FILE_SIZE:
            errors.append(
                f"File too large ({video.file_size / (1024*1024):.1f}MB). "
                f"Maximum size: {self.MAX_FILE_SIZE / (1024*1024):.0f}MB"
            )
        
        # Check aspect ratio
        if video.aspect_ratio and video.aspect_ratio not in self.ASPECT_RATIOS:
            warnings.append(
                f"Aspect ratio '{video.aspect_ratio}' may not be optimal. "
                f"Recommended: {', '.join(self.ASPECT_RATIOS)}"
            )
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
    
    def get_platform_limits(self) -> PlatformLimits:
        """
        Return TikTok platform limits.
        
        Returns:
            PlatformLimits with TikTok-specific constraints
        """
        return PlatformLimits(
            max_caption_length=self.MAX_CAPTION_LENGTH,
            max_hashtags=self.MAX_HASHTAGS,
            max_video_duration=self.MAX_VIDEO_DURATION,
            min_video_duration=self.MIN_VIDEO_DURATION,
            max_file_size=self.MAX_FILE_SIZE,
            supported_formats=self.SUPPORTED_FORMATS,
            supported_resolutions=self.SUPPORTED_RESOLUTIONS,
            aspect_ratios=self.ASPECT_RATIOS,
        )
