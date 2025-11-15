"""
Instagram platform adapter implementation.
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


class InstagramAdapter(PlatformAdapter):
    """
    Instagram platform adapter using Instagram Graph API.
    Implements OAuth 2.0 flow and Reels video upload functionality.
    Requires Business or Creator account.
    """
    
    # Instagram API endpoints
    AUTH_URL = "https://api.instagram.com/oauth/authorize"
    TOKEN_URL = "https://api.instagram.com/oauth/access_token"
    GRAPH_API_URL = "https://graph.instagram.com/v18.0"
    
    # Instagram Reels limits
    MAX_CAPTION_LENGTH = 2200
    MAX_HASHTAGS = 30
    MAX_VIDEO_DURATION = 90  # Reels can be up to 90 seconds
    MIN_VIDEO_DURATION = 3
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    SUPPORTED_FORMATS = ["mp4", "mov"]
    SUPPORTED_RESOLUTIONS = ["720p", "1080p"]
    ASPECT_RATIOS = ["9:16", "4:5", "1:1"]  # Vertical, portrait, or square
    
    def _get_platform_name(self) -> str:
        """Return platform name."""
        return "instagram"
    
    def get_authorization_url(self, state: str, scope: Optional[str] = None) -> str:
        """
        Generate Instagram OAuth authorization URL.
        
        Args:
            state: State parameter for CSRF protection
            scope: OAuth scopes (default: basic, content publishing)
            
        Returns:
            Authorization URL
        """
        if scope is None:
            scope = "instagram_basic,instagram_content_publish"
        
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
            PlatformTokens with access token (Instagram uses long-lived tokens)
            
        Raises:
            PlatformAuthError: If authentication fails
        """
        async with httpx.AsyncClient() as client:
            try:
                # Step 1: Get short-lived token
                response = await client.post(
                    self.TOKEN_URL,
                    data={
                        "client_id": self.client_id,
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
                        f"Instagram authentication failed: {error_data.get('error_message', 'Unknown error')}",
                        platform=self.platform_name,
                        details=error_data,
                    )
                
                data = response.json()
                short_lived_token = data["access_token"]
                user_id = data["user_id"]
                
                # Step 2: Exchange for long-lived token (60 days)
                long_lived_response = await client.get(
                    f"{self.GRAPH_API_URL}/access_token",
                    params={
                        "grant_type": "ig_exchange_token",
                        "client_secret": self.client_secret,
                        "access_token": short_lived_token,
                    },
                    timeout=30.0,
                )
                
                if long_lived_response.status_code != 200:
                    # Fall back to short-lived token if exchange fails
                    expires_at = datetime.utcnow() + timedelta(hours=1)
                    access_token = short_lived_token
                else:
                    long_lived_data = long_lived_response.json()
                    access_token = long_lived_data["access_token"]
                    expires_in = long_lived_data.get("expires_in", 5184000)  # 60 days default
                    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                # Get username
                username = await self._get_username(access_token, user_id)
                
                return PlatformTokens(
                    access_token=access_token,
                    refresh_token=None,  # Instagram uses long-lived tokens
                    expires_at=expires_at,
                    platform_user_id=str(user_id),
                    platform_username=username,
                )
                
            except httpx.RequestError as e:
                raise PlatformAuthError(
                    f"Network error during Instagram authentication: {str(e)}",
                    platform=self.platform_name,
                )
    
    async def _get_username(self, access_token: str, user_id: str) -> str:
        """Get Instagram username."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.GRAPH_API_URL}/{user_id}",
                params={
                    "fields": "username",
                    "access_token": access_token,
                },
                timeout=30.0,
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("username", "")
            
            return ""
    
    async def refresh_token(self, refresh_token: str) -> PlatformTokens:
        """
        Refresh Instagram access token.
        
        Instagram uses long-lived tokens that can be refreshed before expiry.
        
        Args:
            refresh_token: Current access token (Instagram doesn't use separate refresh tokens)
            
        Returns:
            PlatformTokens with refreshed access token
            
        Raises:
            PlatformAuthError: If token refresh fails
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.GRAPH_API_URL}/refresh_access_token",
                    params={
                        "grant_type": "ig_refresh_token",
                        "access_token": refresh_token,
                    },
                    timeout=30.0,
                )
                
                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    raise PlatformAuthError(
                        f"Instagram token refresh failed: {error_data.get('error', {}).get('message', 'Unknown error')}",
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
                    f"Network error during Instagram token refresh: {str(e)}",
                    platform=self.platform_name,
                )
    
    async def upload_video(
        self,
        video_path: str,
        metadata: PostMetadata,
        access_token: str
    ) -> PlatformPost:
        """
        Upload and post video to Instagram as a Reel.
        
        Instagram uses a two-step process:
        1. Create a media container with video URL
        2. Publish the container
        
        Args:
            video_path: Local path to video file (must be publicly accessible URL for Instagram)
            metadata: Post metadata (caption, hashtags, etc.)
            access_token: Valid access token
            
        Returns:
            PlatformPost with media ID
            
        Raises:
            PlatformAuthError: If access token is invalid
            PlatformRateLimitError: If rate limit is exceeded
            PlatformAPIError: If upload fails
        """
        async with httpx.AsyncClient() as client:
            try:
                # Get Instagram Business Account ID
                me_response = await client.get(
                    f"{self.GRAPH_API_URL}/me",
                    params={
                        "fields": "id",
                        "access_token": access_token,
                    },
                    timeout=30.0,
                )
                
                if me_response.status_code != 200:
                    raise PlatformAuthError(
                        "Failed to get Instagram account info",
                        platform=self.platform_name,
                    )
                
                ig_user_id = me_response.json()["id"]
                
                # Prepare caption with hashtags
                caption = metadata.caption
                if metadata.hashtags:
                    caption += "\n\n" + " ".join(f"#{tag}" for tag in metadata.hashtags)
                
                # Note: Instagram requires video to be hosted at a publicly accessible URL
                # In production, this would be an S3 pre-signed URL or similar
                # For now, we'll assume video_path is a URL
                video_url = video_path if video_path.startswith("http") else f"file://{video_path}"
                
                # Step 1: Create media container
                container_params = {
                    "media_type": "REELS",
                    "video_url": video_url,
                    "caption": caption[:self.MAX_CAPTION_LENGTH],
                    "share_to_feed": True,
                    "access_token": access_token,
                }
                
                container_response = await client.post(
                    f"{self.GRAPH_API_URL}/{ig_user_id}/media",
                    data=container_params,
                    timeout=60.0,
                )
                
                # Handle rate limiting
                if container_response.status_code == 429:
                    retry_after = int(container_response.headers.get("Retry-After", 60))
                    raise PlatformRateLimitError(
                        "Instagram rate limit exceeded",
                        platform=self.platform_name,
                        retry_after=retry_after,
                    )
                
                # Handle auth errors
                if container_response.status_code == 401:
                    raise PlatformAuthError(
                        "Instagram access token is invalid or expired",
                        platform=self.platform_name,
                    )
                
                if container_response.status_code != 200:
                    error_data = container_response.json() if container_response.text else {}
                    raise PlatformAPIError(
                        f"Instagram container creation failed: {error_data.get('error', {}).get('message', 'Unknown error')}",
                        platform=self.platform_name,
                        status_code=container_response.status_code,
                        details=error_data,
                    )
                
                container_data = container_response.json()
                container_id = container_data["id"]
                
                # Step 2: Publish the container
                publish_response = await client.post(
                    f"{self.GRAPH_API_URL}/{ig_user_id}/media_publish",
                    data={
                        "creation_id": container_id,
                        "access_token": access_token,
                    },
                    timeout=60.0,
                )
                
                if publish_response.status_code != 200:
                    error_data = publish_response.json() if publish_response.text else {}
                    raise PlatformAPIError(
                        f"Instagram publish failed: {error_data.get('error', {}).get('message', 'Unknown error')}",
                        platform=self.platform_name,
                        status_code=publish_response.status_code,
                        details=error_data,
                    )
                
                publish_data = publish_response.json()
                media_id = publish_data["id"]
                
                return PlatformPost(
                    platform_post_id=media_id,
                    platform_url=f"https://www.instagram.com/reel/{media_id}",
                    posted_at=datetime.utcnow(),
                    status="published",
                    additional_data={"media_id": media_id, "container_id": container_id},
                )
                
            except httpx.RequestError as e:
                raise PlatformAPIError(
                    f"Network error during Instagram upload: {str(e)}",
                    platform=self.platform_name,
                )
    
    async def get_video_analytics(
        self,
        platform_post_id: str,
        access_token: str
    ) -> VideoAnalytics:
        """
        Fetch video analytics from Instagram.
        
        Args:
            platform_post_id: Instagram media ID
            access_token: Valid access token
            
        Returns:
            VideoAnalytics with available metrics
            
        Raises:
            PlatformAuthError: If access token is invalid
            PlatformAPIError: If API request fails
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.GRAPH_API_URL}/{platform_post_id}/insights",
                    params={
                        "metric": "plays,likes,comments,shares,saved",
                        "access_token": access_token,
                    },
                    timeout=30.0,
                )
                
                if response.status_code == 401:
                    raise PlatformAuthError(
                        "Instagram access token is invalid or expired",
                        platform=self.platform_name,
                    )
                
                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    raise PlatformAPIError(
                        f"Instagram analytics fetch failed: {error_data.get('error', {}).get('message', 'Unknown error')}",
                        platform=self.platform_name,
                        status_code=response.status_code,
                        details=error_data,
                    )
                
                data = response.json()
                
                # Parse insights
                metrics = {}
                for item in data.get("data", []):
                    metric_name = item["name"]
                    metric_value = item["values"][0]["value"] if item.get("values") else 0
                    metrics[metric_name] = metric_value
                
                return VideoAnalytics(
                    views=metrics.get("plays", 0),
                    likes=metrics.get("likes", 0),
                    comments=metrics.get("comments", 0),
                    shares=metrics.get("shares", 0),
                    additional_metrics={
                        "saved": metrics.get("saved", 0),
                    },
                )
                
            except httpx.RequestError as e:
                raise PlatformAPIError(
                    f"Network error during Instagram analytics fetch: {str(e)}",
                    platform=self.platform_name,
                )
    
    def validate_video(self, video: Video) -> ValidationResult:
        """
        Validate video against Instagram Reels requirements.
        
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
                f"Maximum duration for Reels: {self.MAX_VIDEO_DURATION}s"
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
                f"Aspect ratio '{video.aspect_ratio}' may not be optimal for Reels. "
                f"Recommended: {', '.join(self.ASPECT_RATIOS)}"
            )
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
    
    def get_platform_limits(self) -> PlatformLimits:
        """
        Return Instagram Reels platform limits.
        
        Returns:
            PlatformLimits with Instagram-specific constraints
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
