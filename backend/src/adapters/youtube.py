"""
YouTube platform adapter implementation.
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


class YouTubeAdapter(PlatformAdapter):
    """
    YouTube platform adapter using YouTube Data API v3.
    Implements OAuth 2.0 flow and video upload functionality for Shorts.
    """
    
    # YouTube API endpoints
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    VIDEO_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
    VIDEO_INFO_URL = "https://www.googleapis.com/youtube/v3/videos"
    ANALYTICS_URL = "https://www.googleapis.com/youtube/v3/videos"
    
    # YouTube Shorts limits
    MAX_CAPTION_LENGTH = 5000
    MAX_HASHTAGS = 15
    MAX_VIDEO_DURATION = 60  # Shorts are max 60 seconds
    MIN_VIDEO_DURATION = 1
    MAX_FILE_SIZE = 256 * 1024 * 1024  # 256MB for Shorts
    SUPPORTED_FORMATS = ["mp4", "mov", "avi", "wmv", "flv", "webm"]
    SUPPORTED_RESOLUTIONS = ["720p", "1080p", "2K", "4K"]
    ASPECT_RATIOS = ["9:16", "1:1"]  # Vertical or square for Shorts
    
    def _get_platform_name(self) -> str:
        """Return platform name."""
        return "youtube"
    
    def get_authorization_url(self, state: str, scope: Optional[str] = None) -> str:
        """
        Generate YouTube OAuth authorization URL.
        
        Args:
            state: State parameter for CSRF protection
            scope: OAuth scopes (default: upload and readonly)
            
        Returns:
            Authorization URL
        """
        if scope is None:
            scope = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"
        
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": scope,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Force consent to get refresh token
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
                        f"YouTube authentication failed: {error_data.get('error_description', 'Unknown error')}",
                        platform=self.platform_name,
                        details=error_data,
                    )
                
                data = response.json()
                
                # Google returns expires_in (seconds)
                expires_in = data.get("expires_in", 3600)  # default 1 hour
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                # Get user info to get channel ID
                user_info = await self._get_user_info(data["access_token"])
                
                return PlatformTokens(
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token"),
                    expires_at=expires_at,
                    platform_user_id=user_info.get("channel_id", ""),
                    platform_username=user_info.get("channel_title", ""),
                    scope=data.get("scope"),
                )
                
            except httpx.RequestError as e:
                raise PlatformAuthError(
                    f"Network error during YouTube authentication: {str(e)}",
                    platform=self.platform_name,
                )
    
    async def exchange_code_for_tokens(self, code: str) -> dict:
        """
        Exchange authorization code for tokens (wrapper for platforms API).
        
        Args:
            code: Authorization code from OAuth callback
            
        Returns:
            Dict with access_token, refresh_token, expires_at, scopes
        """
        tokens = await self.authenticate(code)
        return {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "expires_at": tokens.expires_at,
            "scopes": tokens.scope.split() if tokens.scope else []
        }
    
    async def get_user_info(self, access_token: str) -> dict:
        """
        Get user info from YouTube (wrapper for platforms API).
        
        Args:
            access_token: Valid access token
            
        Returns:
            Dict with id, username, name
        """
        user_info = await self._get_user_info(access_token)
        return {
            "id": user_info.get("channel_id", ""),
            "username": user_info.get("channel_title", ""),
            "name": user_info.get("channel_title", "")
        }
    
    async def _get_user_info(self, access_token: str) -> dict:
        """Get YouTube channel information."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/youtube/v3/channels",
                params={"part": "snippet", "mine": "true"},
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30.0,
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("items"):
                    item = data["items"][0]
                    return {
                        "channel_id": item["id"],
                        "channel_title": item["snippet"]["title"],
                    }
            
            return {}
    
    async def refresh_token(self, refresh_token: str) -> PlatformTokens:
        """
        Refresh YouTube access token.
        
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
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                    },
                    timeout=30.0,
                )
                
                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    raise PlatformAuthError(
                        f"YouTube token refresh failed: {error_data.get('error_description', 'Unknown error')}",
                        platform=self.platform_name,
                        details=error_data,
                    )
                
                data = response.json()
                
                expires_in = data.get("expires_in", 3600)
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                return PlatformTokens(
                    access_token=data["access_token"],
                    refresh_token=refresh_token,  # Google doesn't return new refresh token
                    expires_at=expires_at,
                    platform_user_id="",  # Not returned in refresh
                    scope=data.get("scope"),
                )
                
            except httpx.RequestError as e:
                raise PlatformAuthError(
                    f"Network error during YouTube token refresh: {str(e)}",
                    platform=self.platform_name,
                )
    
    async def upload_video(
        self,
        video_path: str,
        metadata: PostMetadata,
        access_token: str
    ) -> PlatformPost:
        """
        Upload and post video to YouTube as a Short.
        
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
                # Prepare video metadata
                # Add #Shorts hashtag to mark as Short
                title = metadata.caption[:100] if len(metadata.caption) > 100 else metadata.caption
                description = metadata.caption
                if metadata.hashtags:
                    description += "\n\n" + " ".join(f"#{tag}" for tag in metadata.hashtags)
                
                # Ensure #Shorts is included
                if "#Shorts" not in description and "#shorts" not in description:
                    description += " #Shorts"
                
                video_metadata = {
                    "snippet": {
                        "title": title,
                        "description": description,
                        "categoryId": "22",  # People & Blogs category
                    },
                    "status": {
                        "privacyStatus": metadata.privacy_level.lower(),
                        "selfDeclaredMadeForKids": False,
                    }
                }
                
                # Read video file
                with open(video_path, "rb") as video_file:
                    video_data = video_file.read()
                
                # Upload video using multipart upload (proper format)
                import json
                metadata_json = json.dumps(video_metadata)
                
                # Create multipart body
                boundary = "===============7330845974216740156=="
                body_parts = []
                
                # Part 1: JSON metadata
                body_parts.append(f"--{boundary}")
                body_parts.append("Content-Type: application/json; charset=UTF-8")
                body_parts.append("")
                body_parts.append(metadata_json)
                
                # Part 2: Video data
                body_parts.append(f"--{boundary}")
                body_parts.append("Content-Type: video/*")
                body_parts.append("")
                
                # Join text parts
                body_text = "\r\n".join(body_parts) + "\r\n"
                
                # Combine with video data and closing boundary
                body = body_text.encode('utf-8') + video_data + f"\r\n--{boundary}--\r\n".encode('utf-8')
                
                response = await client.post(
                    self.VIDEO_UPLOAD_URL,
                    params={
                        "part": "snippet,status",
                        "uploadType": "multipart",
                    },
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": f"multipart/related; boundary={boundary}",
                    },
                    content=body,
                    timeout=300.0,  # 5 minutes for upload
                )
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    raise PlatformRateLimitError(
                        "YouTube rate limit exceeded",
                        platform=self.platform_name,
                        retry_after=retry_after,
                    )
                
                # Handle auth errors
                if response.status_code == 401:
                    raise PlatformAuthError(
                        "YouTube access token is invalid or expired",
                        platform=self.platform_name,
                    )
                
                if response.status_code not in (200, 201):
                    error_data = response.json() if response.text else {}
                    raise PlatformAPIError(
                        f"YouTube upload failed: {error_data.get('error', {}).get('message', 'Unknown error')}",
                        platform=self.platform_name,
                        status_code=response.status_code,
                        details=error_data,
                    )
                
                data = response.json()
                video_id = data["id"]
                
                return PlatformPost(
                    platform_post_id=video_id,
                    platform_url=f"https://www.youtube.com/shorts/{video_id}",
                    posted_at=datetime.utcnow(),
                    status="published",
                    additional_data={"video_id": video_id},
                )
                
            except httpx.RequestError as e:
                raise PlatformAPIError(
                    f"Network error during YouTube upload: {str(e)}",
                    platform=self.platform_name,
                )
    
    async def get_video_analytics(
        self,
        platform_post_id: str,
        access_token: str
    ) -> VideoAnalytics:
        """
        Fetch video analytics from YouTube.
        
        Args:
            platform_post_id: YouTube video ID
            access_token: Valid access token
            
        Returns:
            VideoAnalytics with views, likes, comments
            
        Raises:
            PlatformAuthError: If access token is invalid
            PlatformAPIError: If API request fails
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self.ANALYTICS_URL,
                    params={
                        "part": "statistics",
                        "id": platform_post_id,
                    },
                    headers={
                        "Authorization": f"Bearer {access_token}",
                    },
                    timeout=30.0,
                )
                
                if response.status_code == 401:
                    raise PlatformAuthError(
                        "YouTube access token is invalid or expired",
                        platform=self.platform_name,
                    )
                
                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    raise PlatformAPIError(
                        f"YouTube analytics fetch failed: {error_data.get('error', {}).get('message', 'Unknown error')}",
                        platform=self.platform_name,
                        status_code=response.status_code,
                        details=error_data,
                    )
                
                data = response.json()
                
                if not data.get("items"):
                    return VideoAnalytics(views=0, likes=0, comments=0, shares=0)
                
                stats = data["items"][0].get("statistics", {})
                
                return VideoAnalytics(
                    views=int(stats.get("viewCount", 0)),
                    likes=int(stats.get("likeCount", 0)),
                    comments=int(stats.get("commentCount", 0)),
                    shares=0,  # YouTube API doesn't provide share count
                    additional_metrics={
                        "favorites": int(stats.get("favoriteCount", 0)),
                    },
                )
                
            except httpx.RequestError as e:
                raise PlatformAPIError(
                    f"Network error during YouTube analytics fetch: {str(e)}",
                    platform=self.platform_name,
                )
    
    def validate_video(self, video: Video) -> ValidationResult:
        """
        Validate video against YouTube Shorts requirements.
        
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
        
        # Check duration for Shorts
        if video.duration < self.MIN_VIDEO_DURATION:
            errors.append(
                f"Video too short ({video.duration}s). "
                f"Minimum duration: {self.MIN_VIDEO_DURATION}s"
            )
        
        if video.duration > self.MAX_VIDEO_DURATION:
            warnings.append(
                f"Video longer than {self.MAX_VIDEO_DURATION}s will not be classified as a Short. "
                f"It will be uploaded as a regular video."
            )
        
        # Check file size
        if video.file_size > self.MAX_FILE_SIZE:
            errors.append(
                f"File too large ({video.file_size / (1024*1024):.1f}MB). "
                f"Maximum size for Shorts: {self.MAX_FILE_SIZE / (1024*1024):.0f}MB"
            )
        
        # Check aspect ratio for Shorts
        if video.aspect_ratio and video.aspect_ratio not in self.ASPECT_RATIOS:
            warnings.append(
                f"Aspect ratio '{video.aspect_ratio}' is not optimal for Shorts. "
                f"Recommended: {', '.join(self.ASPECT_RATIOS)} (vertical or square)"
            )
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
    
    def get_platform_limits(self) -> PlatformLimits:
        """
        Return YouTube Shorts platform limits.
        
        Returns:
            PlatformLimits with YouTube-specific constraints
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
