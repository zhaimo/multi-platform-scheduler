"""
Platform adapters for social media platforms.
"""
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
from .tiktok import TikTokAdapter
from .youtube import YouTubeAdapter
from .instagram import InstagramAdapter
from .facebook import FacebookAdapter

__all__ = [
    "PlatformAdapter",
    "PlatformAuthError",
    "PlatformRateLimitError",
    "PlatformAPIError",
    "PlatformTokens",
    "PostMetadata",
    "PlatformPost",
    "VideoAnalytics",
    "ValidationResult",
    "PlatformLimits",
    "Video",
    "TikTokAdapter",
    "YouTubeAdapter",
    "InstagramAdapter",
    "FacebookAdapter",
]
