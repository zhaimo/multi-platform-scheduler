"""
Application monitoring and metrics collection.
"""
import time
from typing import Optional
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

from .config import settings
from .logging_config import get_logger

logger = get_logger(__name__)

# Prometheus Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'HTTP requests currently in progress',
    ['method', 'endpoint']
)

video_uploads_total = Counter(
    'video_uploads_total',
    'Total video uploads',
    ['status']
)

video_posts_total = Counter(
    'video_posts_total',
    'Total video posts',
    ['platform', 'status']
)

platform_api_calls_total = Counter(
    'platform_api_calls_total',
    'Total platform API calls',
    ['platform', 'operation', 'status']
)

platform_api_duration_seconds = Histogram(
    'platform_api_duration_seconds',
    'Platform API call duration in seconds',
    ['platform', 'operation']
)

celery_tasks_total = Counter(
    'celery_tasks_total',
    'Total Celery tasks',
    ['task_name', 'status']
)

database_connections = Gauge(
    'database_connections',
    'Number of active database connections'
)

redis_connections = Gauge(
    'redis_connections',
    'Number of active Redis connections'
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics for HTTP requests."""
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and collect metrics.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response from handler
        """
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
        
        method = request.method
        endpoint = request.url.path
        
        # Track in-progress requests
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()
        
        # Track request duration
        start_time = time.time()
        
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception as e:
            status = 500
            raise
        finally:
            # Record metrics
            duration = time.time() - start_time
            http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
            http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
            http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()
        
        return response


def setup_sentry(dsn: Optional[str] = None) -> None:
    """
    Initialize Sentry error tracking.
    
    Args:
        dsn: Sentry DSN (Data Source Name). If None, uses SENTRY_DSN env var.
    """
    sentry_dsn = dsn or getattr(settings, 'sentry_dsn', None)
    
    if not sentry_dsn:
        logger.info("Sentry DSN not configured, skipping Sentry initialization")
        return
    
    try:
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=settings.app_env,
            traces_sample_rate=0.1 if settings.app_env == "production" else 1.0,
            profiles_sample_rate=0.1 if settings.app_env == "production" else 1.0,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
                RedisIntegration(),
                CeleryIntegration(),
            ],
            # Send PII (Personally Identifiable Information) - set to False in production
            send_default_pii=False,
            # Release tracking
            release=getattr(settings, 'app_version', '0.1.0'),
            # Before send hook to filter sensitive data
            before_send=before_send_sentry,
        )
        logger.info(f"Sentry initialized for environment: {settings.app_env}")
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {str(e)}")


def before_send_sentry(event, hint):
    """
    Filter sensitive data before sending to Sentry.
    
    Args:
        event: Sentry event dictionary
        hint: Additional context
        
    Returns:
        Modified event or None to drop the event
    """
    # Remove sensitive headers
    if 'request' in event and 'headers' in event['request']:
        headers = event['request']['headers']
        sensitive_headers = ['authorization', 'cookie', 'x-api-key']
        for header in sensitive_headers:
            if header in headers:
                headers[header] = '[Filtered]'
    
    # Remove sensitive query parameters
    if 'request' in event and 'query_string' in event['request']:
        query = event['request']['query_string']
        if query and ('token' in query.lower() or 'key' in query.lower()):
            event['request']['query_string'] = '[Filtered]'
    
    return event


def track_video_upload(status: str) -> None:
    """
    Track video upload metric.
    
    Args:
        status: Upload status (success, failed)
    """
    video_uploads_total.labels(status=status).inc()


def track_video_post(platform: str, status: str) -> None:
    """
    Track video post metric.
    
    Args:
        platform: Platform name (tiktok, youtube, etc.)
        status: Post status (success, failed)
    """
    video_posts_total.labels(platform=platform, status=status).inc()


def track_platform_api_call(platform: str, operation: str, status: str, duration: float) -> None:
    """
    Track platform API call metrics.
    
    Args:
        platform: Platform name
        operation: API operation (upload, authenticate, etc.)
        status: Call status (success, failed)
        duration: Call duration in seconds
    """
    platform_api_calls_total.labels(platform=platform, operation=operation, status=status).inc()
    platform_api_duration_seconds.labels(platform=platform, operation=operation).observe(duration)


def track_celery_task(task_name: str, status: str) -> None:
    """
    Track Celery task execution.
    
    Args:
        task_name: Name of the Celery task
        status: Task status (success, failed, retry)
    """
    celery_tasks_total.labels(task_name=task_name, status=status).inc()


async def metrics_endpoint() -> Response:
    """
    Prometheus metrics endpoint.
    
    Returns:
        Response with Prometheus metrics in text format
    """
    metrics = generate_latest()
    return Response(content=metrics, media_type=CONTENT_TYPE_LATEST)
