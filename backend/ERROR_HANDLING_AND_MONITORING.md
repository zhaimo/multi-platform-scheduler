# Error Handling and Monitoring Guide

This document explains the error handling and monitoring features implemented in the Multi-Platform Video Scheduler backend.

## Error Handling

### Custom Exception Classes

The application uses custom exception classes defined in `src/exceptions.py` for better error handling and user-friendly error messages.

#### Exception Hierarchy

```
AppException (base)
├── AuthenticationError
│   ├── TokenExpiredError
│   └── InvalidTokenError
├── AuthorizationError
├── ValidationError
│   ├── VideoValidationError
│   └── PlatformValidationError
├── ResourceNotFoundError
├── ResourceAlreadyExistsError
├── PlatformAPIError
│   ├── PlatformAuthError
│   ├── PlatformRateLimitError
│   └── PlatformUploadError
├── StorageError
│   ├── S3UploadError
│   └── S3DownloadError
├── VideoProcessingError
│   └── VideoConversionError
├── DatabaseError
├── RateLimitExceededError
├── ScheduleError
│   └── InvalidScheduleTimeError
└── RepostError
    └── RepostTooSoonError
```

#### Using Custom Exceptions

```python
from src.exceptions import ResourceNotFoundError, ValidationError

# Raise a custom exception
raise ResourceNotFoundError(
    resource_type="Video",
    resource_id="123e4567-e89b-12d3-a456-426614174000"
)

# With additional details
raise ValidationError(
    message="Invalid video format",
    details={"format": "avi", "expected": ["mp4", "mov"]}
)
```

### Global Exception Handlers

All exceptions are caught by global exception handlers in `src/error_handlers.py`:

- **AppException**: Returns structured JSON with error code, message, and details
- **ValidationError**: Returns 422 with field-level validation errors
- **SQLAlchemyError**: Returns 500 with generic database error message
- **Exception**: Catches all unexpected errors and returns 500

### Error Response Format

All errors return a consistent JSON structure:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Video with ID 123 not found",
    "details": {
      "resource_type": "Video",
      "resource_id": "123"
    }
  }
}
```

## Structured Logging

### Configuration

Logging is configured in `src/logging_config.py` with:

- **Development**: Human-readable format with timestamps
- **Production**: JSON format for log aggregation tools

### Log Levels

- **DEBUG**: Detailed information for debugging
- **INFO**: General informational messages
- **WARNING**: Warning messages (e.g., failed login attempts)
- **ERROR**: Error messages with stack traces
- **CRITICAL**: Critical errors requiring immediate attention

### Using Loggers

```python
from src.logging_config import get_logger

logger = get_logger(__name__)

# Log messages
logger.info("User registered successfully", extra={"user_id": user.id})
logger.warning("Failed login attempt", extra={"email": email})
logger.error("Database connection failed", exc_info=True)
```

### Log Context

Use `get_logger_with_context` to add context to all log messages:

```python
from src.logging_config import get_logger_with_context

logger = get_logger_with_context(__name__, user_id="123", request_id="abc")
logger.info("Processing request")  # Automatically includes user_id and request_id
```

## Monitoring

### Sentry Integration

Sentry is integrated for error tracking and performance monitoring.

#### Configuration

Add to `.env`:

```bash
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
APP_VERSION=0.1.0
```

#### Features

- Automatic error capture with stack traces
- Performance monitoring (traces)
- Release tracking
- Environment-specific configuration
- Sensitive data filtering (tokens, passwords)

### Prometheus Metrics

Prometheus metrics are exposed at `/metrics` endpoint.

#### Available Metrics

**HTTP Metrics:**
- `http_requests_total`: Total HTTP requests (by method, endpoint, status)
- `http_request_duration_seconds`: Request duration histogram
- `http_requests_in_progress`: Current in-progress requests

**Application Metrics:**
- `video_uploads_total`: Total video uploads (by status)
- `video_posts_total`: Total video posts (by platform, status)
- `platform_api_calls_total`: Platform API calls (by platform, operation, status)
- `platform_api_duration_seconds`: Platform API call duration
- `celery_tasks_total`: Celery task executions (by task name, status)

**Infrastructure Metrics:**
- `database_connections`: Active database connections
- `redis_connections`: Active Redis connections

#### Using Metrics in Code

```python
from src.monitoring import (
    track_video_upload,
    track_video_post,
    track_platform_api_call,
    track_celery_task
)

# Track video upload
track_video_upload(status="success")

# Track video post
track_video_post(platform="tiktok", status="success")

# Track platform API call
track_platform_api_call(
    platform="tiktok",
    operation="upload",
    status="success",
    duration=2.5
)

# Track Celery task
track_celery_task(task_name="post_video", status="success")
```

### Health Check Endpoints

Multiple health check endpoints are available for monitoring and orchestration:

#### `/health` - Basic Health Check

Simple health check that always returns 200 OK if the service is running.

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "service": "Multi-Platform Video Scheduler",
  "version": "0.1.0"
}
```

#### `/health/detailed` - Detailed Health Check

Checks all dependencies (database, Redis, S3) and returns detailed status.

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "service": "Multi-Platform Video Scheduler",
  "version": "0.1.0",
  "environment": "production",
  "checks": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful"
    },
    "redis": {
      "status": "healthy",
      "message": "Redis connection successful",
      "details": {
        "version": "7.0.0",
        "connected_clients": 5,
        "used_memory_human": "1.2M"
      }
    },
    "s3": {
      "status": "healthy",
      "message": "S3 connection successful",
      "details": {
        "bucket": "video-scheduler-uploads",
        "region": "us-east-1"
      }
    }
  }
}
```

#### `/health/ready` - Readiness Check

For Kubernetes readiness probes. Checks if the service is ready to accept traffic.

```json
{
  "status": "ready",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### `/health/live` - Liveness Check

For Kubernetes liveness probes. Checks if the service is alive.

```json
{
  "status": "alive",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Monitoring Setup

### Prometheus

1. Add Prometheus scrape config:

```yaml
scrape_configs:
  - job_name: 'video-scheduler'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

2. Access metrics at `http://localhost:8000/metrics`

### Grafana Dashboard

Create dashboards using the exposed Prometheus metrics:

- Request rate and latency
- Error rates by endpoint
- Video upload/post success rates
- Platform API performance
- Celery task execution metrics

### Sentry

1. Sign up at [sentry.io](https://sentry.io)
2. Create a new project
3. Copy the DSN
4. Add to `.env`: `SENTRY_DSN=your-dsn-here`
5. Restart the application

### Kubernetes Health Checks

Add to your Kubernetes deployment:

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

## Best Practices

### Error Handling

1. **Use specific exceptions**: Use the most specific exception class for the error
2. **Include context**: Add relevant details to exception details
3. **Log before raising**: Log errors with context before raising exceptions
4. **Don't expose internals**: Use user-friendly messages, not internal error details

### Logging

1. **Use appropriate levels**: DEBUG for development, INFO for production events
2. **Add context**: Include relevant IDs and metadata in log messages
3. **Avoid PII**: Don't log sensitive user information
4. **Use structured logging**: Use the `extra` parameter for structured data

### Monitoring

1. **Track key metrics**: Focus on business-critical metrics
2. **Set up alerts**: Configure alerts for error rates and performance degradation
3. **Monitor dependencies**: Track health of external services (S3, platforms)
4. **Review regularly**: Regularly review metrics and logs for issues

## Troubleshooting

### Logs Not Appearing

- Check log level configuration in `src/logging_config.py`
- Verify `DEBUG` setting in `.env`
- Check if logs are being written to stdout

### Metrics Not Updating

- Verify Prometheus middleware is registered in `main.py`
- Check if `/metrics` endpoint is accessible
- Ensure metrics are being tracked in code

### Sentry Not Capturing Errors

- Verify `SENTRY_DSN` is set in `.env`
- Check Sentry initialization in `main.py`
- Verify network connectivity to Sentry
- Check Sentry project settings

### Health Checks Failing

- Check database connectivity
- Verify Redis is running
- Ensure S3 credentials are correct
- Review detailed health check response for specific failures
