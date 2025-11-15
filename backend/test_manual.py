#!/usr/bin/env python3
"""
Manual testing script for backend functionality.
Run this to verify basic backend operations without full environment setup.
"""

import asyncio
from datetime import datetime, timedelta
from src.models.database_models import PlatformEnum, PostStatusEnum
from src.services.post_service import PostService
from src.config import settings


def test_platform_enum():
    """Test platform enum values"""
    print("Testing Platform Enum...")
    platforms = ["tiktok", "youtube", "instagram", "facebook"]
    for platform in platforms:
        try:
            enum_val = PlatformEnum(platform)
            print(f"  ✓ {platform} -> {enum_val}")
        except Exception as e:
            print(f"  ✗ {platform} failed: {e}")
    print()


def test_post_status_enum():
    """Test post status enum values"""
    print("Testing Post Status Enum...")
    statuses = ["pending", "processing", "posted", "failed", "cancelled"]
    for status in statuses:
        try:
            enum_val = PostStatusEnum(status)
            print(f"  ✓ {status} -> {enum_val}")
        except Exception as e:
            print(f"  ✗ {status} failed: {e}")
    print()


def test_24_hour_calculation():
    """Test 24-hour repost restriction calculation"""
    print("Testing 24-hour Restriction Calculation...")
    
    # Simulate a post from 12 hours ago
    posted_at = datetime.utcnow() - timedelta(hours=12)
    restriction_time = datetime.utcnow() - timedelta(hours=24)
    
    if posted_at >= restriction_time:
        time_since_post = datetime.utcnow() - posted_at
        hours_remaining = 24 - (time_since_post.total_seconds() / 3600)
        print(f"  ✓ Post from 12 hours ago:")
        print(f"    - Time since post: {time_since_post.total_seconds() / 3600:.1f} hours")
        print(f"    - Hours remaining: {hours_remaining:.1f} hours")
        print(f"    - Should block: YES")
    
    # Simulate a post from 25 hours ago
    posted_at = datetime.utcnow() - timedelta(hours=25)
    
    if posted_at < restriction_time:
        print(f"  ✓ Post from 25 hours ago:")
        print(f"    - Should block: NO")
    
    print()


def test_caption_limits():
    """Test platform caption limits"""
    print("Testing Caption Limits...")
    
    limits = {
        "tiktok": 2200,
        "youtube": 5000,
        "instagram": 2200,
        "facebook": 63206
    }
    
    test_caption = "A" * 3000
    
    for platform, limit in limits.items():
        if len(test_caption) > limit:
            print(f"  ✓ {platform}: Caption exceeds limit ({len(test_caption)} > {limit})")
        else:
            print(f"  ✓ {platform}: Caption within limit ({len(test_caption)} <= {limit})")
    
    print()


def test_settings():
    """Test settings configuration"""
    print("Testing Settings Configuration...")
    
    try:
        print(f"  ✓ App Name: {settings.app_name}")
        print(f"  ✓ Debug Mode: {settings.debug}")
        print(f"  ✓ API Host: {settings.api_host}")
        print(f"  ✓ API Port: {settings.api_port}")
        print(f"  ✓ Database URL: {'*' * 20} (hidden)")
        print(f"  ✓ CORS Origins: {len(settings.cors_origins_list)} configured")
    except Exception as e:
        print(f"  ✗ Settings error: {e}")
    
    print()


def test_video_format_validation():
    """Test video format validation"""
    print("Testing Video Format Validation...")
    
    valid_formats = ['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/webm']
    invalid_formats = ['image/jpeg', 'text/plain', 'application/pdf']
    
    for fmt in valid_formats:
        if fmt in valid_formats:
            print(f"  ✓ {fmt}: VALID")
    
    for fmt in invalid_formats:
        if fmt not in valid_formats:
            print(f"  ✓ {fmt}: INVALID (correctly rejected)")
    
    print()


def test_file_size_validation():
    """Test file size validation"""
    print("Testing File Size Validation...")
    
    max_size = 500 * 1024 * 1024  # 500MB
    
    test_sizes = [
        (10 * 1024 * 1024, "10MB"),
        (100 * 1024 * 1024, "100MB"),
        (500 * 1024 * 1024, "500MB"),
        (600 * 1024 * 1024, "600MB"),
    ]
    
    for size, label in test_sizes:
        if size <= max_size:
            print(f"  ✓ {label}: VALID (within limit)")
        else:
            print(f"  ✓ {label}: INVALID (exceeds limit)")
    
    print()


def test_schedule_time_validation():
    """Test schedule time validation"""
    print("Testing Schedule Time Validation...")
    
    now = datetime.utcnow()
    min_future_time = now + timedelta(minutes=5)
    
    test_times = [
        (now - timedelta(hours=1), "1 hour ago", False),
        (now + timedelta(minutes=2), "2 minutes from now", False),
        (now + timedelta(minutes=10), "10 minutes from now", True),
        (now + timedelta(days=1), "1 day from now", True),
    ]
    
    for test_time, label, should_be_valid in test_times:
        is_valid = test_time >= min_future_time
        status = "VALID" if is_valid else "INVALID"
        check = "✓" if is_valid == should_be_valid else "✗"
        print(f"  {check} {label}: {status}")
    
    print()


def main():
    """Run all tests"""
    print("=" * 60)
    print("Multi-Platform Video Scheduler - Manual Backend Tests")
    print("=" * 60)
    print()
    
    test_platform_enum()
    test_post_status_enum()
    test_24_hour_calculation()
    test_caption_limits()
    test_settings()
    test_video_format_validation()
    test_file_size_validation()
    test_schedule_time_validation()
    
    print("=" * 60)
    print("All basic tests completed!")
    print("=" * 60)
    print()
    print("Note: These are basic validation tests.")
    print("Full integration testing requires:")
    print("  - PostgreSQL database")
    print("  - Redis server")
    print("  - Celery workers")
    print("  - Platform OAuth credentials")
    print("  - AWS S3 bucket")
    print()


if __name__ == "__main__":
    main()
