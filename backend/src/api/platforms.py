"""
Platform OAuth API endpoints for connecting social media accounts.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any
import logging
from datetime import datetime, timedelta
import secrets

from ..database import get_db
from ..models.database_models import User, PlatformConnection
from ..utils.auth import get_current_user
from ..config import get_settings
from ..adapters.youtube import YouTubeAdapter
from ..adapters.tiktok import TikTokAdapter
from ..adapters.twitter import TwitterAdapter
from ..adapters.instagram import InstagramAdapter
from ..adapters.facebook import FacebookAdapter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth/platforms", tags=["platforms"])

# Platform adapter mapping
PLATFORM_ADAPTERS = {
    "youtube": YouTubeAdapter,
    "tiktok": TikTokAdapter,
    "twitter": TwitterAdapter,
    "instagram": InstagramAdapter,
    "facebook": FacebookAdapter,
}

# In-memory state storage (in production, use Redis)
# Note: This will be cleared on server restart
oauth_states = {}


@router.get("/{platform}/authorize")
async def authorize_platform(
    platform: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Initiate OAuth flow for a platform.
    Returns the authorization URL for the frontend to redirect to.
    """
    print(f"[AUTHORIZE ENDPOINT HIT] Platform: {platform}, User: {current_user.id}")
    logger.info(f"[AUTHORIZE ENDPOINT HIT] Platform: {platform}, User: {current_user.id}")
    
    if platform not in PLATFORM_ADAPTERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported platform: {platform}"
        )
    
    try:
        logger.info(f"[DEBUG] Starting OAuth for {platform}, user: {current_user.id}")
        
        # Generate state parameter for CSRF protection
        state = secrets.token_urlsafe(32)
        oauth_states[state] = {
            "user_id": str(current_user.id),
            "platform": platform,
            "created_at": datetime.utcnow()
        }
        logger.info(f"[DEBUG] Generated state: {state[:10]}...")
        logger.info(f"[DEBUG] Stored state in oauth_states. Total states: {len(oauth_states)}")
        
        # Clean up old states (older than 10 minutes)
        cutoff = datetime.utcnow() - timedelta(minutes=10)
        for k in list(oauth_states.keys()):
            if oauth_states[k]["created_at"] < cutoff:
                del oauth_states[k]
        logger.info(f"[DEBUG] Cleaned up old states")
        
        # Get platform adapter
        logger.info(f"[DEBUG] Getting settings...")
        settings = get_settings()
        logger.info(f"[DEBUG] Got settings, getting adapter class...")
        adapter_class = PLATFORM_ADAPTERS[platform]
        logger.info(f"[DEBUG] Got adapter class: {adapter_class}")
        
        # Get platform-specific credentials
        logger.info(f"[DEBUG] Creating adapter instance for {platform}...")
        if platform == "youtube":
            logger.info(f"[DEBUG] YouTube credentials - client_id: {settings.youtube_client_id[:20]}...")
            adapter = adapter_class(
                client_id=settings.youtube_client_id,
                client_secret=settings.youtube_client_secret,
                redirect_uri=settings.youtube_redirect_uri
            )
            logger.info(f"[DEBUG] YouTube adapter created")
        elif platform == "tiktok":
            adapter = adapter_class(
                client_id=settings.tiktok_client_key,
                client_secret=settings.tiktok_client_secret,
                redirect_uri=settings.tiktok_redirect_uri
            )
        elif platform == "twitter":
            adapter = adapter_class(
                client_id=settings.twitter_client_id,
                client_secret=settings.twitter_client_secret,
                redirect_uri=settings.twitter_redirect_uri
            )
        elif platform == "instagram":
            adapter = adapter_class(
                client_id=settings.instagram_client_id,
                client_secret=settings.instagram_client_secret,
                redirect_uri=settings.instagram_redirect_uri
            )
        elif platform == "facebook":
            adapter = adapter_class(
                client_id=settings.facebook_app_id,
                client_secret=settings.facebook_app_secret,
                redirect_uri=settings.facebook_redirect_uri
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported platform: {platform}"
            )
        
        # Generate authorization URL
        logger.info(f"[DEBUG] Calling get_authorization_url...")
        auth_url = adapter.get_authorization_url(state)
        logger.info(f"[DEBUG] Got auth URL: {auth_url[:50]}...")
        
        logger.info(f"Generated {platform} OAuth URL for user {current_user.id}")
        return {"authorization_url": auth_url}
        
    except Exception as e:
        logger.error(f"Error initiating {platform} OAuth for user {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate {platform} authorization: {str(e)}"
        )


@router.get("/{platform}/callback")
async def platform_callback(
    platform: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle OAuth callback from platform.
    """
    if platform not in PLATFORM_ADAPTERS:
        settings = get_settings()
        return RedirectResponse(
            url=f"{settings.frontend_url}/dashboard/platforms?error=unsupported_platform"
        )
    
    try:
        # Get query parameters
        query_params = dict(request.query_params)
        code = query_params.get("code")
        state = query_params.get("state")
        error = query_params.get("error")
        
        settings = get_settings()
        
        # Handle OAuth errors
        if error:
            logger.warning(f"{platform} OAuth error: {error}")
            return RedirectResponse(
                url=f"{settings.frontend_url}/dashboard/platforms?error=oauth_denied"
            )
        
        if not code or not state:
            logger.warning(f"{platform} OAuth callback missing code or state")
            return RedirectResponse(
                url=f"{settings.frontend_url}/dashboard/platforms?error=invalid_callback"
            )
        
        # Verify state parameter
        # For Twitter, state includes code_verifier: "state:code_verifier"
        code_verifier = None
        actual_state = state
        if platform == "twitter" and ":" in state:
            parts = state.split(":", 1)
            actual_state = parts[0]
            code_verifier = parts[1]
        
        logger.info(f"[DEBUG] Callback received. State: {actual_state[:10]}..., Total states in memory: {len(oauth_states)}")
        logger.info(f"[DEBUG] Available states: {[s[:10] for s in oauth_states.keys()]}")
        if actual_state not in oauth_states:
            logger.warning(f"Invalid OAuth state: {actual_state}")
            logger.warning(f"[DEBUG] State not found. Available: {list(oauth_states.keys())}")
            return RedirectResponse(
                url=f"{settings.frontend_url}/dashboard/platforms?error=invalid_state"
            )
        
        state_data = oauth_states[actual_state]
        user_id = state_data["user_id"]
        
        # Clean up used state
        del oauth_states[actual_state]
        
        # Get platform adapter
        adapter_class = PLATFORM_ADAPTERS[platform]
        
        # Get platform-specific credentials
        if platform == "youtube":
            adapter = adapter_class(
                client_id=settings.youtube_client_id,
                client_secret=settings.youtube_client_secret,
                redirect_uri=settings.youtube_redirect_uri
            )
        elif platform == "tiktok":
            adapter = adapter_class(
                client_id=settings.tiktok_client_key,
                client_secret=settings.tiktok_client_secret,
                redirect_uri=settings.tiktok_redirect_uri
            )
        elif platform == "twitter":
            adapter = adapter_class(
                client_id=settings.twitter_client_id,
                client_secret=settings.twitter_client_secret,
                redirect_uri=settings.twitter_redirect_uri
            )
        elif platform == "instagram":
            adapter = adapter_class(
                client_id=settings.instagram_client_id,
                client_secret=settings.instagram_client_secret,
                redirect_uri=settings.instagram_redirect_uri
            )
        elif platform == "facebook":
            adapter = adapter_class(
                client_id=settings.facebook_app_id,
                client_secret=settings.facebook_app_secret,
                redirect_uri=settings.facebook_redirect_uri
            )
        
        # Exchange code for tokens
        if platform == "twitter":
            token_data = await adapter.exchange_code_for_tokens(code, code_verifier)
        else:
            token_data = await adapter.exchange_code_for_tokens(code)
        
        # Get user info from platform
        user_info = await adapter.get_user_info(token_data["access_token"])
        
        # Convert platform string to enum (uppercase to match database)
        from ..models.database_models import PlatformEnum
        platform_enum = PlatformEnum(platform.upper())
        
        # Save or update platform connection
        stmt = select(PlatformConnection).where(
            PlatformConnection.user_id == user_id,
            PlatformConnection.platform == platform_enum
        )
        result = await db.execute(stmt)
        connection = result.scalar_one_or_none()
        
        if connection:
            # Update existing connection
            connection.access_token = token_data["access_token"]
            connection.refresh_token = token_data.get("refresh_token")
            connection.token_expires_at = token_data.get("expires_at")
            connection.platform_user_id = user_info.get("id")
            connection.platform_username = user_info.get("username") or user_info.get("name")
            connection.scopes = token_data.get("scopes", [])
            connection.is_active = True
            connection.updated_at = datetime.utcnow()
        else:
            # Create new connection
            connection = PlatformConnection(
                user_id=user_id,
                platform=platform_enum,
                platform_user_id=user_info.get("id"),
                platform_username=user_info.get("username") or user_info.get("name"),
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_expires_at=token_data.get("expires_at"),
                scopes=token_data.get("scopes", []),
                is_active=True
            )
            db.add(connection)
        
        await db.commit()
        
        logger.info(f"Successfully connected {platform} for user {user_id}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/dashboard/platforms?success={platform}_connected"
        )
        
    except Exception as e:
        logger.error(f"Error handling {platform} OAuth callback: {str(e)}", exc_info=True)
        return RedirectResponse(
            url=f"{settings.frontend_url}/dashboard/platforms?error=connection_failed"
        )


@router.delete("/{platform}")
async def disconnect_platform(
    platform: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Disconnect a platform connection.
    """
    if platform not in PLATFORM_ADAPTERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported platform: {platform}"
        )
    
    try:
        # Find and deactivate connection
        from ..models.database_models import PlatformEnum
        platform_enum = PlatformEnum(platform.upper())
        
        stmt = select(PlatformConnection).where(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.platform == platform_enum,
            PlatformConnection.is_active == True
        )
        result = await db.execute(stmt)
        connection = result.scalar_one_or_none()
        
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active {platform} connection found"
            )
        
        # Deactivate connection (keep for audit trail)
        connection.is_active = False
        connection.updated_at = datetime.utcnow()
        await db.commit()
        
        logger.info(f"Disconnected {platform} for user {current_user.id}")
        return {"message": f"Successfully disconnected {platform}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting {platform} for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect {platform}"
        )


@router.get("/connected")
async def get_connected_platforms(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all connected platforms for the current user.
    """
    try:
        # Get all active connections for user
        stmt = select(PlatformConnection).where(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.is_active == True
        )
        result = await db.execute(stmt)
        connections = result.scalars().all()
        
        # Build response
        platforms = []
        for conn in connections:
            platforms.append({
                "platform": conn.platform.value.lower(),  # Convert to lowercase for frontend
                "platform_user_id": conn.platform_user_id,
                "platform_username": conn.platform_username,
                "is_active": conn.is_active,
                "connected_at": conn.created_at.isoformat(),
                "scopes": conn.scopes
            })
        
        return {"platforms": platforms}
        
    except Exception as e:
        logger.error(f"Error getting connected platforms for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get connected platforms"
        )


@router.get("/status")
async def get_platform_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get connection status for all platforms.
    """
    try:
        # Get all active connections for user
        stmt = select(PlatformConnection).where(
            PlatformConnection.user_id == current_user.id,
            PlatformConnection.is_active == True
        )
        result = await db.execute(stmt)
        connections = result.scalars().all()
        
        # Build status dict
        status = {}
        for platform in PLATFORM_ADAPTERS.keys():
            # Compare with uppercase since enum values are uppercase
            connection = next((c for c in connections if c.platform.value.lower() == platform), None)
            if connection:
                status[platform] = {
                    "connected": True,
                    "username": connection.platform_username,
                    "connected_at": connection.created_at.isoformat(),
                    "scopes": connection.scopes
                }
            else:
                status[platform] = {
                    "connected": False,
                    "username": None,
                    "connected_at": None,
                    "scopes": []
                }
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting platform status for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get platform status"
        )
