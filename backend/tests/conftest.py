"""
Pytest configuration and fixtures.
"""
import os
import pytest
from cryptography.fernet import Fernet

# Set test environment variables before importing app modules
os.environ.update({
    "APP_ENV": "test",
    "DEBUG": "true",
    "SECRET_KEY": "test-secret-key-for-testing-only",
    "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test_db",
    "REDIS_URL": "redis://localhost:6379/1",
    "CELERY_BROKER_URL": "redis://localhost:6379/1",
    "CELERY_RESULT_BACKEND": "redis://localhost:6379/1",
    "JWT_SECRET_KEY": "test-jwt-secret-key-for-testing-only-change-in-production",
    "JWT_ALGORITHM": "HS256",
    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "15",
    "JWT_REFRESH_TOKEN_EXPIRE_DAYS": "7",
    "AWS_ACCESS_KEY_ID": "test-aws-key",
    "AWS_SECRET_ACCESS_KEY": "test-aws-secret",
    "AWS_REGION": "us-east-1",
    "S3_BUCKET_NAME": "test-bucket",
    "TIKTOK_CLIENT_KEY": "test-tiktok-key",
    "TIKTOK_CLIENT_SECRET": "test-tiktok-secret",
    "TIKTOK_REDIRECT_URI": "http://localhost:3000/callback",
    "YOUTUBE_CLIENT_ID": "test-youtube-id",
    "YOUTUBE_CLIENT_SECRET": "test-youtube-secret",
    "YOUTUBE_REDIRECT_URI": "http://localhost:3000/callback",
    "INSTAGRAM_CLIENT_ID": "test-instagram-id",
    "INSTAGRAM_CLIENT_SECRET": "test-instagram-secret",
    "INSTAGRAM_REDIRECT_URI": "http://localhost:3000/callback",
    "FACEBOOK_APP_ID": "test-facebook-id",
    "FACEBOOK_APP_SECRET": "test-facebook-secret",
    "FACEBOOK_REDIRECT_URI": "http://localhost:3000/callback",
    "ENCRYPTION_KEY": Fernet.generate_key().decode(),
})
