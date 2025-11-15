"""
Platform adapter base classes and common error types.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel


# Error Classes
class PlatformError(Exception):
    """Base exception for platform-related errors."""
    def __init__(self, message: str, platform: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.platform = platform
        self.details = details or {}
        super().__init__(self.message)


class PlatformAuthError(PlatformError):
    """Raised when platform authentication fails."""
    pass


class PlatformRateLimitError(PlatformError):
    """Raised when platform rate limit is exceeded."""
    def __init__(self, message: str, platform: str, retry_after: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, platform, details)
        self.retry_after = retry_after  # seconds to wait before retry


class PlatformAPIError(PlatformError):
    """Raised when platform API returns an error."""
    def __init__(self, message: str, platform: str, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, platform, details)
        self.status_code = status_code


# Data Models
class PlatformTokens(BaseModel):
    """OAuth tokens returned by platform."""
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: datetime
    platform_user_id: str
    platform_username: Optional[str] = None
    scope: Optional[str] = None


class PostMetadata(BaseModel):
    """Metadata for posting a video."""
    caption: str
    hashtags: list[str] = []
    privacy_level: str = "public"
    disable_comments: bool = False
    disable_duet: bool = False
    disable_stitch: bool = False
    additional_params: Dict[str, Any] = {}


class PlatformPost(BaseModel):
    """Result of posting a video to a platform."""
    platform_post_id: str
    platform_url: Optional[str] = None
    posted_at: datetime
    status: str  # "published", "processing", "failed"
    additional_data: Dict[str, Any] = {}


class VideoAnalytics(BaseModel):
    """Video performance metrics from a platform."""
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    engagement_rate: Optional[float] = None
    additional_metrics: Dict[str, Any] = {}


class ValidationResult(BaseModel):
    """Result of video validation."""
    is_valid: bool
    errors: list[str] = []
    warnings: list[str] = []


class PlatformLimits(BaseModel):
    """Platform-specific limits and requirements."""
    max_caption_length: int
    max_hashtags: int
    max_video_duration: int  # seconds
    min_video_duration: int  # seconds
    max_file_size: int  # bytes
    supported_formats: list[str]
    supported_resolutions: list[str]
    aspect_ratios: list[str]


class Video(BaseModel):
    """Video information for validation."""
    file_path: str
    duration: int  # seconds
    format: str
    resolution: str
    file_size: int  # bytes
    aspect_ratio: Optional[str] = None


# Abstract Base Class
class PlatformAdapter(ABC):
    """
    Abstract base class for platform adapters.
    Each platform (TikTok, YouTube, Instagram, Facebook) implements this interface.
    """
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """
        Initialize platform adapter.
        
        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
            redirect_uri: OAuth redirect URI
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.platform_name = self._get_platform_name()
    
    @abstractmethod
    def _get_platform_name(self) -> str:
        """Return the platform name (e.g., 'tiktok', 'youtube')."""
        pass
    
    @abstractmethod
    async def authenticate(self, auth_code: str) -> PlatformTokens:
        """
        Handle OAuth authentication and exchange code for tokens.
        
        Args:
            auth_code: Authorization code from OAuth callback
            
        Returns:
            PlatformTokens with access token and refresh token
            
        Raises:
            PlatformAuthError: If authentication fails
        """
        pass
    
    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> PlatformTokens:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token from previous authentication
            
        Returns:
            PlatformTokens with new access token
            
        Raises:
            PlatformAuthError: If token refresh fails
        """
        pass
    
    @abstractmethod
    async def upload_video(
        self,
        video_path: str,
        metadata: PostMetadata,
        access_token: str
    ) -> PlatformPost:
        """
        Upload and post video to platform.
        
        Args:
            video_path: Local path to video file
            metadata: Post metadata (caption, hashtags, etc.)
            access_token: Valid access token
            
        Returns:
            PlatformPost with post ID and URL
            
        Raises:
            PlatformAuthError: If access token is invalid
            PlatformRateLimitError: If rate limit is exceeded
            PlatformAPIError: If upload fails
        """
        pass
    
    @abstractmethod
    async def get_video_analytics(
        self,
        platform_post_id: str,
        access_token: str
    ) -> VideoAnalytics:
        """
        Fetch video performance metrics from platform.
        
        Args:
            platform_post_id: Platform-specific video/post ID
            access_token: Valid access token
            
        Returns:
            VideoAnalytics with views, likes, comments, shares
            
        Raises:
            PlatformAuthError: If access token is invalid
            PlatformAPIError: If API request fails
        """
        pass
    
    @abstractmethod
    def validate_video(self, video: Video) -> ValidationResult:
        """
        Check if video meets platform requirements.
        
        Args:
            video: Video information to validate
            
        Returns:
            ValidationResult with validation status and errors
        """
        pass
    
    @abstractmethod
    def get_platform_limits(self) -> PlatformLimits:
        """
        Return platform-specific limits and requirements.
        
        Returns:
            PlatformLimits with caption length, file size, etc.
        """
        pass
    
    def get_authorization_url(self, state: str) -> str:
        """
        Generate OAuth authorization URL.
        
        Args:
            state: State parameter for CSRF protection
            
        Returns:
            Authorization URL to redirect user to
        """
        raise NotImplementedError("Subclass must implement get_authorization_url")
