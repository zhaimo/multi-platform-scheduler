"""
Authentication API endpoints.
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..database import get_db
from ..models import (
    User,
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
)
from ..utils.auth import AuthUtils, get_current_user
from ..config import settings
from ..exceptions import (
    ResourceAlreadyExistsError,
    AuthenticationError,
    ResourceNotFoundError,
    InvalidTokenError,
)
from ..logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user.
    
    Args:
        user_data: User registration data (email, password)
        db: Database session
        
    Returns:
        TokenResponse with access and refresh tokens
        
    Raises:
        HTTPException: If email already exists
    """
    # Check if user already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        logger.warning(f"Registration attempt with existing email: {user_data.email}")
        raise ResourceAlreadyExistsError(
            resource_type="User",
            message="Email already registered"
        )
    
    # Hash password
    password_hash = AuthUtils.hash_password(user_data.password)
    
    # Create new user
    new_user = User(
        email=user_data.email,
        password_hash=password_hash,
        notification_preferences={}
    )
    
    try:
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        logger.info(f"New user registered: {new_user.email}")
    except IntegrityError:
        await db.rollback()
        logger.warning(f"Registration failed due to integrity error: {user_data.email}")
        raise ResourceAlreadyExistsError(
            resource_type="User",
            message="Email already registered"
        )
    
    # Generate tokens
    access_token = AuthUtils.create_access_token(
        data={"sub": str(new_user.id)},
        expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    
    refresh_token = AuthUtils.create_refresh_token(
        data={"sub": str(new_user.id)},
        expires_delta=timedelta(days=settings.jwt_refresh_token_expire_days)
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens.
    
    Args:
        credentials: User login credentials (email, password)
        db: Database session
        
    Returns:
        TokenResponse with access and refresh tokens
        
    Raises:
        HTTPException: If credentials are invalid
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()
    
    # Verify user exists and password is correct
    if not user or not AuthUtils.verify_password(credentials.password, user.password_hash):
        logger.warning(f"Failed login attempt for email: {credentials.email}")
        raise AuthenticationError(
            message="Incorrect email or password",
            details={"email": credentials.email}
        )
    
    # Generate tokens
    access_token = AuthUtils.create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    
    refresh_token = AuthUtils.create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(days=settings.jwt_refresh_token_expire_days)
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    
    Args:
        token_data: Refresh token
        db: Database session
        
    Returns:
        TokenResponse with new access and refresh tokens
        
    Raises:
        HTTPException: If refresh token is invalid
    """
    # Decode and validate refresh token
    payload = AuthUtils.decode_token(token_data.refresh_token)
    
    # Verify it's a refresh token
    AuthUtils.verify_token_type(payload, "refresh")
    
    # Extract user ID
    user_id: str = payload.get("sub")
    if user_id is None:
        logger.warning("Refresh token missing user ID")
        raise InvalidTokenError(message="Invalid refresh token")
    
    # Verify user exists
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        logger.warning(f"Refresh token for non-existent user: {user_id}")
        raise ResourceNotFoundError(resource_type="User", resource_id=user_id)
    
    # Generate new tokens
    access_token = AuthUtils.create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    
    new_refresh_token = AuthUtils.create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(days=settings.jwt_refresh_token_expire_days)
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    
    Args:
        current_user: Current authenticated user from JWT token
        
    Returns:
        UserResponse with user information
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        created_at=current_user.created_at,
        notification_preferences=current_user.notification_preferences
    )


# Platform OAuth endpoints
from fastapi import Query
from fastapi.responses import RedirectResponse
from ..adapters.tiktok import TikTokAdapter
from ..adapters.youtube import YouTubeAdapter
from ..adapters.instagram import InstagramAdapter
from ..adapters.facebook import FacebookAdapter
from ..models.database_models import PlatformAuth, PlatformEnum
import secrets
from datetime import datetime


@router.delete("/platforms/{platform}/disconnect")
async def disconnect_platform(
    platform: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Disconnect a platform for current user.
    
    Args:
        platform: Platform name (tiktok, youtube, instagram, facebook)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Success message
    """
    # Validate platform
    try:
        platform_enum = PlatformEnum(platform.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid platform: {platform}"
        )
    
    # Find platform auth
    result = await db.execute(
        select(PlatformAuth).where(
            PlatformAuth.user_id == current_user.id,
            PlatformAuth.platform == platform_enum
        )
    )
    platform_auth = result.scalar_one_or_none()
    
    if not platform_auth:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Platform {platform} not connected"
        )
    
    # Deactivate instead of delete to preserve history
    platform_auth.is_active = False
    platform_auth.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": f"Successfully disconnected {platform}"}
