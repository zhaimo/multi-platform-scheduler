"""
Custom exception classes for the application.
"""
from typing import Optional, Dict, Any


class AppException(Exception):
    """Base exception class for application errors."""
    
    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize application exception.
        
        Args:
            message: User-friendly error message
            code: Error code for programmatic handling
            status_code: HTTP status code
            details: Additional error details
        """
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


# Authentication & Authorization Errors
class AuthenticationError(AppException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="AUTH_ERROR",
            status_code=401,
            details=details
        )


class AuthorizationError(AppException):
    """Raised when user lacks permission for an action."""
    
    def __init__(self, message: str = "You don't have permission to perform this action", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=403,
            details=details
        )


class TokenExpiredError(AuthenticationError):
    """Raised when JWT token has expired."""
    
    def __init__(self, message: str = "Token has expired", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, details=details)
        self.code = "TOKEN_EXPIRED"


class InvalidTokenError(AuthenticationError):
    """Raised when JWT token is invalid."""
    
    def __init__(self, message: str = "Invalid token", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, details=details)
        self.code = "INVALID_TOKEN"


# Validation Errors
class ValidationError(AppException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400,
            details=details
        )


class VideoValidationError(ValidationError):
    """Raised when video validation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, details=details)
        self.code = "VIDEO_VALIDATION_ERROR"


class PlatformValidationError(ValidationError):
    """Raised when platform-specific validation fails."""
    
    def __init__(self, platform: str, message: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["platform"] = platform
        super().__init__(message=message, details=details)
        self.code = "PLATFORM_VALIDATION_ERROR"


# Resource Errors
class ResourceNotFoundError(AppException):
    """Raised when a requested resource is not found."""
    
    def __init__(self, resource_type: str, resource_id: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details.update({"resource_type": resource_type, "resource_id": resource_id})
        super().__init__(
            message=f"{resource_type} with ID {resource_id} not found",
            code="RESOURCE_NOT_FOUND",
            status_code=404,
            details=details
        )


class ResourceAlreadyExistsError(AppException):
    """Raised when attempting to create a resource that already exists."""
    
    def __init__(self, resource_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["resource_type"] = resource_type
        super().__init__(
            message=message,
            code="RESOURCE_ALREADY_EXISTS",
            status_code=409,
            details=details
        )


# Platform API Errors
class PlatformAPIError(AppException):
    """Base class for platform API errors."""
    
    def __init__(self, platform: str, message: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["platform"] = platform
        super().__init__(
            message=message,
            code="PLATFORM_API_ERROR",
            status_code=502,
            details=details
        )


class PlatformAuthError(PlatformAPIError):
    """Raised when platform authentication fails."""
    
    def __init__(self, platform: str, message: str = "Platform authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(platform=platform, message=message, details=details)
        self.code = "PLATFORM_AUTH_ERROR"


class PlatformRateLimitError(PlatformAPIError):
    """Raised when platform rate limit is exceeded."""
    
    def __init__(self, platform: str, retry_after: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(
            platform=platform,
            message=f"Rate limit exceeded for {platform}. Please try again later.",
            details=details
        )
        self.code = "PLATFORM_RATE_LIMIT"
        self.status_code = 429


class PlatformUploadError(PlatformAPIError):
    """Raised when video upload to platform fails."""
    
    def __init__(self, platform: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(platform=platform, message=message, details=details)
        self.code = "PLATFORM_UPLOAD_ERROR"


# Storage Errors
class StorageError(AppException):
    """Base class for storage-related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="STORAGE_ERROR",
            status_code=500,
            details=details
        )


class S3UploadError(StorageError):
    """Raised when S3 upload fails."""
    
    def __init__(self, message: str = "Failed to upload file to storage", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, details=details)
        self.code = "S3_UPLOAD_ERROR"


class S3DownloadError(StorageError):
    """Raised when S3 download fails."""
    
    def __init__(self, message: str = "Failed to download file from storage", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, details=details)
        self.code = "S3_DOWNLOAD_ERROR"


# Video Processing Errors
class VideoProcessingError(AppException):
    """Raised when video processing fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VIDEO_PROCESSING_ERROR",
            status_code=500,
            details=details
        )


class VideoConversionError(VideoProcessingError):
    """Raised when video conversion fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, details=details)
        self.code = "VIDEO_CONVERSION_ERROR"


# Database Errors
class DatabaseError(AppException):
    """Raised when database operation fails."""
    
    def __init__(self, message: str = "Database operation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=500,
            details=details
        )


# Rate Limiting Errors
class RateLimitExceededError(AppException):
    """Raised when user exceeds rate limit."""
    
    def __init__(self, message: str = "Rate limit exceeded. Please try again later.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details=details
        )


# Schedule Errors
class ScheduleError(AppException):
    """Raised when scheduling operation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="SCHEDULE_ERROR",
            status_code=400,
            details=details
        )


class InvalidScheduleTimeError(ScheduleError):
    """Raised when schedule time is invalid."""
    
    def __init__(self, message: str = "Invalid schedule time", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, details=details)
        self.code = "INVALID_SCHEDULE_TIME"


# Repost Errors
class RepostError(AppException):
    """Raised when repost operation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="REPOST_ERROR",
            status_code=400,
            details=details
        )


class RepostTooSoonError(RepostError):
    """Raised when attempting to repost within 24-hour window."""
    
    def __init__(self, platform: str, hours_remaining: float, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details.update({"platform": platform, "hours_remaining": hours_remaining})
        super().__init__(
            message=f"Cannot repost to {platform} yet. Please wait {hours_remaining:.1f} more hours.",
            details=details
        )
        self.code = "REPOST_TOO_SOON"
