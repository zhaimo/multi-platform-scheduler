"""Input validation and sanitization utilities"""

import os
import magic
from typing import Optional, List
from fastapi import UploadFile, HTTPException
from src.logging_config import get_logger

logger = get_logger(__name__)

# Maximum file size: 500MB
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB in bytes

# Allowed video MIME types
ALLOWED_VIDEO_TYPES = [
    "video/mp4",
    "video/quicktime",  # MOV
    "video/x-msvideo",  # AVI
    "video/webm",
    "video/x-matroska",  # MKV
]

# Allowed video extensions
ALLOWED_VIDEO_EXTENSIONS = [".mp4", ".mov", ".avi", ".webm", ".mkv"]


class FileValidator:
    """Validator for file uploads"""
    
    @staticmethod
    async def validate_video_file(file: UploadFile) -> None:
        """
        Validate video file upload.
        
        Args:
            file: The uploaded file
            
        Raises:
            HTTPException: If validation fails
        """
        # Check file size
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024 * 1024):.0f}MB"
            )
        
        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="File is empty"
            )
        
        # Check file extension
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ALLOWED_VIDEO_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File extension {file_ext} not allowed. Allowed extensions: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
            )
        
        # Check MIME type using python-magic
        try:
            # Read first 2048 bytes for magic number detection
            file_header = await file.read(2048)
            file.file.seek(0)
            
            mime = magic.from_buffer(file_header, mime=True)
            
            if mime not in ALLOWED_VIDEO_TYPES:
                logger.warning(
                    f"File upload rejected: MIME type {mime} not allowed",
                    extra={"filename": file.filename, "mime_type": mime}
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"File type {mime} not allowed. Allowed types: video files only"
                )
        except Exception as e:
            logger.error(f"Error validating file MIME type: {e}")
            raise HTTPException(
                status_code=400,
                detail="Unable to validate file type"
            )
        
        logger.info(
            f"File validation passed",
            extra={
                "file_name": file.filename,
                "file_size": file_size,
                "mime_type": mime
            }
        )
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent path traversal and other attacks.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove path components
        filename = os.path.basename(filename)
        
        # Remove or replace dangerous characters
        dangerous_chars = ['..', '/', '\\', '\0', '\n', '\r']
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        
        # Limit filename length
        name, ext = os.path.splitext(filename)
        if len(name) > 200:
            name = name[:200]
        
        return name + ext


class InputSanitizer:
    """Sanitizer for text inputs"""
    
    @staticmethod
    def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize text input by removing potentially dangerous content.
        
        Args:
            text: Input text
            max_length: Maximum allowed length
            
        Returns:
            Sanitized text
        """
        if not text:
            return text
        
        # Remove null bytes
        text = text.replace('\0', '')
        
        # Trim whitespace
        text = text.strip()
        
        # Enforce max length
        if max_length and len(text) > max_length:
            text = text[:max_length]
        
        return text
    
    @staticmethod
    def sanitize_tags(tags: List[str], max_tags: int = 50, max_tag_length: int = 50) -> List[str]:
        """
        Sanitize list of tags.
        
        Args:
            tags: List of tags
            max_tags: Maximum number of tags allowed
            max_tag_length: Maximum length per tag
            
        Returns:
            Sanitized list of tags
        """
        if not tags:
            return []
        
        # Limit number of tags
        tags = tags[:max_tags]
        
        # Sanitize each tag
        sanitized = []
        for tag in tags:
            tag = InputSanitizer.sanitize_text(tag, max_tag_length)
            if tag:  # Only include non-empty tags
                sanitized.append(tag)
        
        return sanitized
    
    @staticmethod
    def sanitize_hashtags(hashtags: List[str], max_hashtags: int = 30) -> List[str]:
        """
        Sanitize list of hashtags.
        
        Args:
            hashtags: List of hashtags
            max_hashtags: Maximum number of hashtags allowed
            
        Returns:
            Sanitized list of hashtags
        """
        if not hashtags:
            return []
        
        # Limit number of hashtags
        hashtags = hashtags[:max_hashtags]
        
        # Sanitize each hashtag
        sanitized = []
        for hashtag in hashtags:
            # Remove # if present
            hashtag = hashtag.lstrip('#')
            
            # Remove special characters except underscore
            hashtag = ''.join(c for c in hashtag if c.isalnum() or c == '_')
            
            # Limit length
            hashtag = hashtag[:100]
            
            if hashtag:  # Only include non-empty hashtags
                sanitized.append(hashtag)
        
        return sanitized


def validate_file_size_middleware(max_size: int = MAX_FILE_SIZE):
    """
    Middleware to validate file size before processing.
    
    Args:
        max_size: Maximum allowed file size in bytes
    """
    async def check_file_size(request):
        content_length = request.headers.get('content-length')
        if content_length:
            content_length = int(content_length)
            if content_length > max_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"Request body too large. Maximum size: {max_size / (1024 * 1024):.0f}MB"
                )
    
    return check_file_size
