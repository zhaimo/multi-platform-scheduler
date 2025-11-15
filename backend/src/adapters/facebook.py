"""
Facebook platform adapter implementation.
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


class FacebookAdapter(PlatformAdapter):
    """
    Facebook platform adapter using Facebook Graph API.
    Implements OAuth 2.0 flow and video post functionality.
    """
    
    # Facebook API endpoints
    AUTH_URL = "https://www.facebook.com/v18.0/dialog/oauth"
    TOKEN_URL = "https://graph.facebook.com/v18.0/oauth/access_token"
    GRAPH_API_URL = "https://graph.facebook.com/v18.0"
    
    # Facebook video limits
    MAX_CAPTION_LENGTH = 63206
    MAX_HASHTAGS = 30
    MAX_VIDEO_DURATION = 240 * 60  # 240 minutes
    MIN_VIDEO_DURATION = 1
    MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10GB
    SUPPORTED_FORMATS = ["mp4", "mov", "avi", "wmv", "flv", "webm", "mkv"]
    SUPPORTED_RESOLUTIONS = ["720p", "1080p", "2K", "4K"]
    ASPECT_RATIOS = ["9:16", "16:9", "1:1", "4:5"]
    
    def _get_platform_name(self) -> str:
        """Return platform name."""
        return "facebook"
    
    def get_authorization_url(self, state: str, scope: Optional[str] = None) -> str:
        """
        Generate Facebook OAuth authorization URL.
        
        Args:
            state: State parameter for CSRF protection
            scope: OAuth scopes (default: pages_manage_posts, pages_read_engagement)
            
        Returns:
            Authorization URL
        """
        if scope is None:
            scope = "pages_manage_posts,pages_read_engagement,pages_show_list"
        
        params = {
            "client_id": self.client_id,
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
                # Step 1: Get short-lived user access token
                response = await client.get(
                    self.TOKEN_URL,
                    params={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": auth_code,
                        "redirect_uri": self.redirect_uri,
                    },
                    timeout=30.0,
                )
                
                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    raise PlatformAuthError(
                        f"Facebook authentication failed: {error_data.get('error', {}).get('message', 'Unknown error')}",
                        platform=self.platform_name,
                        details=error_data,
                    )
                
                data = response.json()
                short_lived_token = data["access_token"]
                
                # Step 2: Exchange for long-lived token (60 days)
                long_lived_response = await client.get(
                    self.TOKEN_URL,
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "fb_exchange_token": short_lived_token,
                    },
                    timeout=30.0,
                )
                
                if long_lived_response.status_code != 200:
                    # Fall back to short-lived token
                    access_token = short_lived_token
                    expires_in = data.get("expires_in", 3600)
                else:
                    long_lived_data = long_lived_response.json()
                    access_token = long_lived_data["access_token"]
                    expires_in = long_lived_data.get("expires_in", 5184000)  # 60 days
                
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                # Get user info
                user_info = await self._get_user_info(access_token)
                
                return PlatformTokens(
                    access_token=access_token,
                    refresh_token=None,  # Facebook uses long-lived tokens
                    expires_at=expires_at,
                    platform_user_id=user_info.get("id", ""),
                    platform_username=user_info.get("name", ""),
                )
                
            except httpx.RequestError as e:
                raise PlatformAuthError(
                    f"Network error during Facebook authentication: {str(e)}",
                    platform=self.platform_name,
                )
    
    async def _get_user_info(self, access_token: str) -> dict:
        """Get Facebook user information."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.GRAPH_API_URL}/me",
                params={
                    "fields": "id,name",
                    "access_token": access_token,
                },
                timeout=30.0,
            )
            
            if response.status_code == 200:
                return response.json()
            
            return {}
    
    async def refresh_token(self, refresh_token: str) -> PlatformTokens:
        """
        Refresh Facebook access token.
        
        Facebook long-lived tokens can be refreshed to extend their lifetime.
        
        Args:
            refresh_token: Current access token (Facebook doesn't use separate refresh tokens)
            
        Returns:
            PlatformTokens with refreshed access token
            
        Raises:
            PlatformAuthError: If token refresh fails
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self.TOKEN_URL,
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "fb_exchange_token": refresh_token,
                    },
                    timeout=30.0,
                )
                
                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    raise PlatformAuthError(
                        f"Facebook token refresh failed: {error_data.get('error', {}).get('message', 'Unknown error')}",
                        platform=self.platform_name,
                        details=error_data,
                    )
                
                data = response.json()
                
                expires_in = data.get("expires_in", 5184000)  # 60 days
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                return PlatformTokens(
                    access_token=data["access_token"],
                    refresh_token=None,
                    expires_at=expires_at,
                    platform_user_id="",  # Not returned in refresh
                )
                
            except httpx.RequestError as e:
                raise PlatformAuthError(
                    f"Network error during Facebook token refresh: {str(e)}",
                    platform=self.platform_name,
                )
    
    async def upload_video(
        self,
        video_path: str,
        metadata: PostMetadata,
        access_token: str
    ) -> PlatformPost:
        """
        Upload and post video to Facebook.
        
        Facebook uses resumable upload for large videos.
        This implementation uses the simple upload for smaller files.
        
        Args:
            video_path: Local path to video file
            metadata: Post metadata (caption, hashtags, etc.)
            access_token: Valid access token
            
        Returns:
            PlatformPost with video ID and URL
            
        Raises:
            PlatformAuthError: If access token is invalid
            PlatformRateLimitError: If rate limit is exceeded
            PlatformAPIError: If upload fails
        """
        async with httpx.AsyncClient() as client:
            try:
                # Get user's pages (Facebook posts are made to pages)
                pages_response = await client.get(
                    f"{self.GRAPH_API_URL}/me/accounts",
                    params={
                        "access_token": access_token,
                    },
                    timeout=30.0,
                )
                
                if pages_response.status_code != 200:
                    raise PlatformAuthError(
                        "Failed to get Facebook pages",
                        platform=self.platform_name,
                    )
                
                pages_data = pages_response.json()
                
                if not pages_data.get("data"):
                    raise PlatformAPIError(
                        "No Facebook pages found. Video posting requires a Facebook Page.",
                        platform=self.platform_name,
                    )
                
                # Use the first page
                page = pages_data["data"][0]
                page_id = page["id"]
                page_access_token = page["access_token"]
                
                # Prepare caption with hashtags
                description = metadata.caption
                if metadata.hashtags:
                    description += "\n\n" + " ".join(f"#{tag}" for tag in metadata.hashtags)
                
                # Upload video
                with open(video_path, "rb") as video_file:
                    video_data = video_file.read()
                
                upload_response = await client.post(
                    f"{self.GRAPH_API_URL}/{page_id}/videos",
                    data={
                        "description": description[:self.MAX_CAPTION_LENGTH],
                        "access_token": page_access_token,
                    },
                    files={
                        "source": ("video.mp4", video_data, "video/mp4"),
                    },
                    timeout=300.0,  # 5 minutes for upload
                )
                
                # Handle rate limiting
                if upload_response.status_code == 429:
                    retry_after = int(upload_response.headers.get("Retry-After", 60))
                    raise PlatformRateLimitError(
                        "Facebook rate limit exceeded",
                        platform=self.platform_name,
                        retry_after=retry_after,
                    )
                
                # Handle auth errors
                if upload_response.status_code == 401:
                    raise PlatformAuthError(
                        "Facebook access token is invalid or expired",
                        platform=self.platform_name,
                    )
                
                if upload_response.status_code != 200:
                    error_data = upload_response.json() if upload_response.text else {}
                    raise PlatformAPIError(
                        f"Facebook upload failed: {error_data.get('error', {}).get('message', 'Unknown error')}",
                        platform=self.platform_name,
                        status_code=upload_response.status_code,
                        details=error_data,
                    )
                
                data = upload_response.json()
                video_id = data["id"]
                
                return PlatformPost(
                    platform_post_id=video_id,
                    platform_url=f"https://www.facebook.com/{page_id}/videos/{video_id}",
                    posted_at=datetime.utcnow(),
                    status="published",
                    additional_data={
                        "video_id": video_id,
                        "page_id": page_id,
                    },
                )
                
            except httpx.RequestError as e:
                raise PlatformAPIError(
                    f"Network error during Facebook upload: {str(e)}",
                    platform=self.platform_name,
                )
    
    async def get_video_analytics(
        self,
        platform_post_id: str,
        access_token: str
    ) -> VideoAnalytics:
        """
        Fetch video analytics from Facebook.
        
        Args:
            platform_post_id: Facebook video ID
            access_token: Valid access token
            
        Returns:
            VideoAnalytics with views, likes, comments, shares
            
        Raises:
            PlatformAuthError: If access token is invalid
            PlatformAPIError: If API request fails
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.GRAPH_API_URL}/{platform_post_id}",
                    params={
                        "fields": "views,likes.summary(true),comments.summary(true),shares",
                        "access_token": access_token,
                    },
                    timeout=30.0,
                )
                
                if response.status_code == 401:
                    raise PlatformAuthError(
                        "Facebook access token is invalid or expired",
                        platform=self.platform_name,
                    )
                
                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    raise PlatformAPIError(
                        f"Facebook analytics fetch failed: {error_data.get('error', {}).get('message', 'Unknown error')}",
                        platform=self.platform_name,
                        status_code=response.status_code,
                        details=error_data,
                    )
                
                data = response.json()
                
                return VideoAnalytics(
                    views=data.get("views", 0),
                    likes=data.get("likes", {}).get("summary", {}).get("total_count", 0),
                    comments=data.get("comments", {}).get("summary", {}).get("total_count", 0),
                    shares=data.get("shares", {}).get("count", 0),
                )
                
            except httpx.RequestError as e:
                raise PlatformAPIError(
                    f"Network error during Facebook analytics fetch: {str(e)}",
                    platform=self.platform_name,
                )
    
    def validate_video(self, video: Video) -> ValidationResult:
        """
        Validate video against Facebook requirements.
        
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
                f"Maximum duration: {self.MAX_VIDEO_DURATION / 60:.0f} minutes"
            )
        
        # Check file size
        if video.file_size > self.MAX_FILE_SIZE:
            errors.append(
                f"File too large ({video.file_size / (1024*1024*1024):.1f}GB). "
                f"Maximum size: {self.MAX_FILE_SIZE / (1024*1024*1024):.0f}GB"
            )
        
        # Facebook is flexible with aspect ratios, just provide info
        if video.aspect_ratio:
            if video.aspect_ratio not in self.ASPECT_RATIOS:
                warnings.append(
                    f"Aspect ratio '{video.aspect_ratio}' is acceptable but may not be optimal. "
                    f"Common ratios: {', '.join(self.ASPECT_RATIOS)}"
                )
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
    
    def get_platform_limits(self) -> PlatformLimits:
        """
        Return Facebook platform limits.
        
        Returns:
            PlatformLimits with Facebook-specific constraints
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
