"""Application configuration management"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Application
    app_name: str = "Multi-Platform Video Scheduler"
    app_env: str = "development"
    debug: bool = True
    secret_key: str
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Database
    database_url: str
    database_pool_size: int = 20
    database_max_overflow: int = 10
    
    # Redis
    redis_url: str
    celery_broker_url: str
    celery_result_backend: str
    
    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    
    # AWS S3
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "us-east-1"
    s3_bucket_name: str
    s3_presigned_url_expiration: int = 3600
    
    # TikTok
    tiktok_client_key: str
    tiktok_client_secret: str
    tiktok_redirect_uri: str
    
    # YouTube
    youtube_client_id: str
    youtube_client_secret: str
    youtube_redirect_uri: str
    
    # Twitter/X (OAuth 2.0 for auth, OAuth 1.0a for media)
    twitter_client_id: str
    twitter_client_secret: str
    twitter_redirect_uri: str
    twitter_api_key: str = ""  # OAuth 1.0a API Key (optional, for media uploads)
    twitter_api_secret: str = ""  # OAuth 1.0a API Secret (optional, for media uploads)
    twitter_access_token: str = ""  # OAuth 1.0a Access Token (optional, for media uploads)
    twitter_access_token_secret: str = ""  # OAuth 1.0a Access Token Secret (optional, for media uploads)
    
    # Instagram
    instagram_client_id: str
    instagram_client_secret: str
    instagram_redirect_uri: str
    
    # Facebook
    facebook_app_id: str
    facebook_app_secret: str
    facebook_redirect_uri: str
    
    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "Video Scheduler"
    
    # File Upload
    max_upload_size_mb: int = 500
    allowed_video_formats: str = "mp4,mov,avi,webm"
    
    # Rate Limiting
    rate_limit_per_minute: int = 100
    
    # CORS
    cors_origins: str = "http://localhost:3000"
    frontend_url: str = "http://localhost:3000"
    
    # Encryption
    encryption_key: str
    
    # Monitoring (optional)
    sentry_dsn: str = ""
    app_version: str = "0.1.0"
    
    @property
    def allowed_video_formats_list(self) -> List[str]:
        """Get allowed video formats as a list"""
        return [fmt.strip() for fmt in self.allowed_video_formats.split(",")]
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list"""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    # Aliases for platform adapters (they expect client_id)
    @property
    def tiktok_client_id(self) -> str:
        """Alias for tiktok_client_key"""
        return self.tiktok_client_key
    
    @property
    def facebook_client_id(self) -> str:
        """Alias for facebook_app_id"""
        return self.facebook_app_id
    
    @property
    def facebook_client_secret(self) -> str:
        """Alias for facebook_app_secret"""
        return self.facebook_app_secret


# Global settings instance
_settings = None


def get_settings() -> Settings:
    """Get or create settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# For backward compatibility
settings = get_settings()
