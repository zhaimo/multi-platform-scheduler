"""
Authentication utilities for JWT token generation and password hashing.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import hashlib
import base64
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models.database_models import User
from ..exceptions import (
    InvalidTokenError,
    TokenExpiredError,
    ResourceNotFoundError,
)
from ..logging_config import get_logger

logger = get_logger(__name__)

# Password hashing context using Argon2 (more secure than bcrypt and no length limits)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer()


class AuthUtils:
    """Utility class for authentication operations."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using Argon2.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to compare against
            
        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token.
        
        Args:
            data: Dictionary of claims to encode in the token
            expires_delta: Optional expiration time delta (default: 15 minutes)
            
        Returns:
            Encoded JWT token string
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT refresh token.
        
        Args:
            data: Dictionary of claims to encode in the token
            expires_delta: Optional expiration time delta (default: 7 days)
            
        Returns:
            Encoded JWT refresh token string
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=7)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """
        Decode and validate a JWT token.
        
        Args:
            token: JWT token string to decode
            
        Returns:
            Dictionary of decoded claims
            
        Raises:
            InvalidTokenError: If token is invalid
            TokenExpiredError: If token has expired
        """
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise TokenExpiredError()
        except JWTError as e:
            logger.warning(f"Invalid token: {str(e)}")
            raise InvalidTokenError(message="Could not validate credentials")
    
    @staticmethod
    def verify_token_type(payload: Dict[str, Any], expected_type: str) -> None:
        """
        Verify that a token payload has the expected type.
        
        Args:
            payload: Decoded token payload
            expected_type: Expected token type ("access" or "refresh")
            
        Raises:
            InvalidTokenError: If token type doesn't match
        """
        token_type = payload.get("type")
        if token_type != expected_type:
            logger.warning(f"Invalid token type. Expected {expected_type}, got {token_type}")
            raise InvalidTokenError(
                message=f"Invalid token type. Expected {expected_type}",
                details={"expected": expected_type, "actual": token_type}
            )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get the current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials containing the JWT token
        db: Database session
        
    Returns:
        User object for the authenticated user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    
    # Decode and validate token
    payload = AuthUtils.decode_token(token)
    
    # Verify it's an access token
    AuthUtils.verify_token_type(payload, "access")
    
    # Extract user ID from token
    user_id: str = payload.get("sub")
    if user_id is None:
        logger.warning("Token missing user ID")
        raise InvalidTokenError(message="Could not validate credentials")
    
    # Fetch user from database
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        logger.warning(f"User not found for token: {user_id}")
        raise ResourceNotFoundError(resource_type="User", resource_id=user_id)
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    FastAPI dependency to get the current active user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User object if active
        
    Raises:
        HTTPException: If user is inactive
    """
    # Add is_active check if you add that field to User model
    # For now, just return the user
    return current_user


async def get_current_user_from_token(
    token: str,
    db: AsyncSession
) -> Optional[User]:
    """
    Get user from a JWT token string (used by rate limiter).
    
    Args:
        token: JWT token string
        db: Database session
        
    Returns:
        User object if token is valid, None otherwise
    """
    try:
        # Decode and validate token
        payload = AuthUtils.decode_token(token)
        
        # Verify it's an access token
        AuthUtils.verify_token_type(payload, "access")
        
        # Extract user ID from token
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        
        # Fetch user from database
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        return user
    except Exception as e:
        logger.debug(f"Failed to get user from token: {str(e)}")
        return None
