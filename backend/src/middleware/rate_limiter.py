"""Rate limiting middleware using SlowAPI"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request
from src.utils.auth import get_current_user_from_token
from src.logging_config import get_logger

logger = get_logger(__name__)


def get_user_identifier(request: Request) -> str:
    """
    Get user identifier for rate limiting.
    Uses user ID if authenticated, otherwise falls back to IP address.
    """
    try:
        # Try to get user from Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            # Extract user info from token without full validation
            # This is a lightweight check for rate limiting purposes
            from jose import jwt
            from src.config import settings
            
            try:
                payload = jwt.decode(
                    token,
                    settings.jwt_secret_key,
                    algorithms=[settings.jwt_algorithm]
                )
                user_id = payload.get("sub")
                if user_id:
                    return f"user:{user_id}"
            except Exception:
                # If token is invalid, fall back to IP
                pass
    except Exception as e:
        logger.debug(f"Error extracting user for rate limiting: {e}")
    
    # Fall back to IP address
    return get_remote_address(request)


# Initialize rate limiter
# Default: 100 requests per minute per user
# Use in-memory storage for simplicity (Redis can be added later for production)
from src.config import settings

limiter = Limiter(
    key_func=get_user_identifier,
    default_limits=["100/minute"],
    storage_uri="memory://",  # Use in-memory storage
    strategy="fixed-window"
)
logger.info("Rate limiter initialized with in-memory storage")


class RateLimitMiddleware(SlowAPIMiddleware):
    """Custom rate limit middleware with enhanced error handling"""
    
    def __init__(self, app, limiter):
        self.limiter = limiter
        super().__init__(app)
    
    async def __call__(self, scope, receive, send):
        """Handle rate limit exceeded with custom response"""
        try:
            await super().__call__(scope, receive, send)
        except RateLimitExceeded as e:
            # Log rate limit exceeded
            if scope["type"] == "http":
                request = Request(scope, receive)
                identifier = get_user_identifier(request)
                logger.warning(
                    f"Rate limit exceeded for {identifier} on {request.url.path}",
                    extra={
                        "identifier": identifier,
                        "path": request.url.path,
                        "method": request.method
                    }
                )
            raise
