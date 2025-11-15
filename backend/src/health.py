"""
Health check endpoints for monitoring application status.
"""
from typing import Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as aioredis

from .database import get_db
from .config import settings
from .logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


async def check_database(db: AsyncSession) -> Dict[str, Any]:
    """
    Check database connectivity and health.
    
    Args:
        db: Database session
        
    Returns:
        Dictionary with database health status
    """
    try:
        # Execute simple query to check connection
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        
        return {
            "status": "healthy",
            "message": "Database connection successful",
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}",
        }


async def check_redis() -> Dict[str, Any]:
    """
    Check Redis connectivity and health.
    
    Returns:
        Dictionary with Redis health status
    """
    try:
        redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        
        # Ping Redis
        await redis_client.ping()
        
        # Get info
        info = await redis_client.info()
        
        await redis_client.close()
        
        return {
            "status": "healthy",
            "message": "Redis connection successful",
            "details": {
                "version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
            }
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}",
        }


async def check_s3() -> Dict[str, Any]:
    """
    Check S3 connectivity and health.
    
    Returns:
        Dictionary with S3 health status
    """
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region
        )
        
        # Check if bucket exists and is accessible
        s3_client.head_bucket(Bucket=settings.s3_bucket_name)
        
        return {
            "status": "healthy",
            "message": "S3 connection successful",
            "details": {
                "bucket": settings.s3_bucket_name,
                "region": settings.aws_region,
            }
        }
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"S3 health check failed: {error_code}")
        return {
            "status": "unhealthy",
            "message": f"S3 connection failed: {error_code}",
        }
    except Exception as e:
        logger.error(f"S3 health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "message": f"S3 connection failed: {str(e)}",
        }


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Basic health check endpoint.
    
    Returns:
        Simple health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.app_name,
        "version": "0.1.0",
    }


@router.get("/health/detailed", status_code=status.HTTP_200_OK)
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """
    Detailed health check endpoint that checks all dependencies.
    
    Args:
        db: Database session
        
    Returns:
        Detailed health status for all components
    """
    # Check all components
    database_health = await check_database(db)
    redis_health = await check_redis()
    s3_health = await check_s3()
    
    # Determine overall status
    all_healthy = all([
        database_health["status"] == "healthy",
        redis_health["status"] == "healthy",
        s3_health["status"] == "healthy",
    ])
    
    overall_status = "healthy" if all_healthy else "degraded"
    http_status = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    
    response = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.app_name,
        "version": "0.1.0",
        "environment": settings.app_env,
        "checks": {
            "database": database_health,
            "redis": redis_health,
            "s3": s3_health,
        }
    }
    
    return response


@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness check endpoint for Kubernetes/container orchestration.
    
    Args:
        db: Database session
        
    Returns:
        Readiness status
    """
    # Check critical dependencies
    database_health = await check_database(db)
    redis_health = await check_redis()
    
    is_ready = (
        database_health["status"] == "healthy" and
        redis_health["status"] == "healthy"
    )
    
    if not is_ready:
        return {
            "status": "not_ready",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": database_health,
                "redis": redis_health,
            }
        }
    
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_check():
    """
    Liveness check endpoint for Kubernetes/container orchestration.
    
    Returns:
        Liveness status
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
    }
