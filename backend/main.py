"""FastAPI application entry point"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from src.config import settings
from src.api import auth_router
from src.api.videos import router as videos_router
from src.api.posts import router as posts_router
from src.api.schedules import router as schedules_router
from src.api.templates import router as templates_router
from src.api.notifications import router as notifications_router
from src.api.platforms import router as platforms_router
from src.logging_config import setup_logging, get_logger
from src.error_handlers import register_error_handlers
from src.monitoring import setup_sentry, PrometheusMiddleware, metrics_endpoint
from src.health import router as health_router
from src.middleware import limiter, RateLimitMiddleware

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Setup Sentry (if configured)
setup_sentry()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug
)

# Add rate limiter state
app.state.limiter = limiter

# Register error handlers
register_error_handlers(app)

# Add rate limit exceeded handler
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add Prometheus middleware
app.add_middleware(PrometheusMiddleware)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware, limiter=limiter)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(videos_router)
app.include_router(posts_router)
app.include_router(schedules_router)
app.include_router(templates_router)
app.include_router(notifications_router)
app.include_router(platforms_router)
app.include_router(health_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Multi-Platform Video Scheduler API",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return await metrics_endpoint()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
