"""
Twitter/X platform adapter for OAuth 2.0 and video posting.
Uses OAuth 2.0 for authentication and OAuth 1.0a for media uploads.
"""
import httpx
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode
from requests_oauthlib import OAuth1Session
import requests

from .base import (
    PlatformAdapter,
    PlatformTokens,
    PostMetadata,
    PlatformPost,
    VideoAnalytics,
    ValidationResult,
    PlatformLimits,
    Video,
    PlatformAuthError,
    PlatformAPIError,
    PlatformRateLimitError,
)


class TwitterAdapter(PlatformAdapter):
    """Twitter/X platform adapter using OAuth 2.0 with PKCE."""
    
    BASE_URL = "https://api.twitter.com/2"
    AUTH_URL = "https://twitter.com/i/oauth2/authorize"
    TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
    
    def _get_platform_name(self) -> str:
        return "twitter"
    
    def get_authorization_url(self, state: str) -> str:
        """
        Generate Twitter OAuth 2.0 authorization URL with PKCE.
        
        Args:
            state: State parameter for CSRF protection
            
        Returns:
            Authorization URL
        """
        # Generate PKCE code verifier and challenge
        import hashlib
        import base64
        
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        # Store code_verifier with state (in production, use Redis)
        # For now, we'll store it in the state parameter itself (not recommended for production)
        
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "tweet.read tweet.write users.read offline.access media.write",
            "state": f"{state}:{code_verifier}",  # Embed code_verifier in state
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"
    
    async def exchange_code_for_tokens(self, code: str, code_verifier: str = None) -> dict:
        """
        Exchange authorization code for tokens (wrapper for platforms API).
        
        Args:
            code: Authorization code from OAuth callback
            code_verifier: PKCE code verifier (required for Twitter)
            
        Returns:
            Dict with access_token, refresh_token, expires_at, scopes
        """
        if not code_verifier:
            raise PlatformAuthError(
                "Twitter requires code_verifier for PKCE flow",
                self.platform_name
            )
        
        tokens = await self.authenticate(code, code_verifier)
        return {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "expires_at": tokens.expires_at,
            "scopes": tokens.scope.split() if tokens.scope else [],
        }
    
    async def get_user_info(self, access_token: str) -> dict:
        """
        Get user info (wrapper for platforms API).
        
        Args:
            access_token: Access token
            
        Returns:
            Dict with id, username
        """
        user_data = await self._get_user_info(access_token)
        return {
            "id": user_data["id"],
            "username": user_data["username"],
        }
    
    async def authenticate(self, auth_code: str, code_verifier: str) -> PlatformTokens:
        """
        Exchange authorization code for access token.
        
        Args:
            auth_code: Authorization code from OAuth callback
            code_verifier: PKCE code verifier
            
        Returns:
            PlatformTokens with access and refresh tokens
        """
        import base64
        
        # Twitter requires Basic Auth with client credentials
        credentials = f"{self.client_id}:{self.client_secret}"
        b64_credentials = base64.b64encode(credentials.encode()).decode()
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.TOKEN_URL,
                    data={
                        "grant_type": "authorization_code",
                        "code": auth_code,
                        "redirect_uri": self.redirect_uri,
                        "code_verifier": code_verifier,
                    },
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Authorization": f"Basic {b64_credentials}",
                    },
                )
                response.raise_for_status()
                data = response.json()
                
                # Get user info
                user_info = await self._get_user_info(data["access_token"])
                
                return PlatformTokens(
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token"),
                    expires_at=datetime.utcnow() + timedelta(seconds=data.get("expires_in", 7200)),
                    platform_user_id=user_info["id"],
                    platform_username=user_info["username"],
                    scope=data.get("scope"),
                )
            except httpx.HTTPStatusError as e:
                raise PlatformAuthError(
                    f"Twitter authentication failed: {e.response.text}",
                    self.platform_name,
                    {"status_code": e.response.status_code}
                )
            except Exception as e:
                raise PlatformAuthError(
                    f"Twitter authentication error: {str(e)}",
                    self.platform_name
                )
    
    async def refresh_token(self, refresh_token: str) -> PlatformTokens:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            New PlatformTokens
        """
        import base64
        
        # Twitter requires Basic Auth with client credentials
        credentials = f"{self.client_id}:{self.client_secret}"
        b64_credentials = base64.b64encode(credentials.encode()).decode()
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.TOKEN_URL,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                    },
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Authorization": f"Basic {b64_credentials}",
                    },
                )
                response.raise_for_status()
                data = response.json()
                
                # Get user info
                user_info = await self._get_user_info(data["access_token"])
                
                return PlatformTokens(
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token", refresh_token),
                    expires_at=datetime.utcnow() + timedelta(seconds=data.get("expires_in", 7200)),
                    platform_user_id=user_info["id"],
                    platform_username=user_info["username"],
                    scope=data.get("scope"),
                )
            except httpx.HTTPStatusError as e:
                raise PlatformAuthError(
                    f"Twitter token refresh failed: {e.response.text}",
                    self.platform_name,
                    {"status_code": e.response.status_code}
                )
    
    async def _get_user_info(self, access_token: str) -> dict:
        """Get Twitter user information."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/users/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()["data"]
    
    async def upload_video(
        self,
        video_path: str,
        metadata: PostMetadata,
        access_token: str
    ) -> PlatformPost:
        """
        Upload and post video to Twitter using chunked upload.
        
        Twitter requires a three-phase upload process:
        1. INIT - Initialize upload
        2. APPEND - Upload video chunks
        3. FINALIZE - Finalize upload
        4. Create tweet with media_id
        """
        import os
        import time
        
        # Get file size
        file_size = os.path.getsize(video_path)
        
        # Phase 1: INIT
        media_id = await self._init_upload(file_size, access_token)
        
        # Phase 2: APPEND - Upload in chunks
        await self._append_upload(video_path, media_id, access_token)
        
        # Phase 3: FINALIZE
        await self._finalize_upload(media_id, access_token)
        
        # Wait for processing to complete
        await self._wait_for_processing(media_id, access_token)
        
        # Phase 4: Create tweet with video
        tweet_data = await self._create_tweet(media_id, metadata, access_token)
        
        return PlatformPost(
            platform_post_id=tweet_data["id"],
            platform_url=f"https://twitter.com/i/web/status/{tweet_data['id']}",
            posted_at=datetime.utcnow(),
            status="published"
        )
    
    async def _init_upload(self, file_size: int, access_token: str) -> str:
        """Initialize chunked upload using OAuth 1.0a."""
        from src.config import get_settings
        settings = get_settings()
        
        # Check if OAuth 1.0a credentials are configured
        if not settings.twitter_api_key or not settings.twitter_api_secret:
            raise PlatformAPIError(
                "Twitter OAuth 1.0a credentials not configured. Please add TWITTER_API_KEY and TWITTER_API_SECRET to your .env file.",
                self.platform_name
            )
        
        # Use OAuth 1.0a for media upload
        oauth = OAuth1Session(
            settings.twitter_api_key,
            client_secret=settings.twitter_api_secret,
            resource_owner_key=settings.twitter_access_token,
            resource_owner_secret=settings.twitter_access_token_secret
        )
        
        try:
            response = oauth.post(
                "https://upload.twitter.com/1.1/media/upload.json",
                data={
                    "command": "INIT",
                    "total_bytes": file_size,
                    "media_type": "video/mp4",
                    "media_category": "tweet_video"
                }
            )
            response.raise_for_status()
            data = response.json()
            return str(data["media_id_string"])
        except requests.exceptions.HTTPError as e:
            error_text = e.response.text if hasattr(e.response, 'text') else str(e)
            raise PlatformAPIError(
                f"Twitter upload INIT failed: {error_text}",
                self.platform_name,
                status_code=e.response.status_code if hasattr(e, 'response') else None
            )
        except Exception as e:
            raise PlatformAPIError(
                f"Twitter upload INIT failed: {str(e)}",
                self.platform_name
            )
    
    async def _append_upload(self, video_path: str, media_id: str, access_token: str):
        """Upload video in chunks using OAuth 1.0a."""
        from src.config import get_settings
        settings = get_settings()
        
        # Use OAuth 1.0a for media upload
        oauth = OAuth1Session(
            settings.twitter_api_key,
            client_secret=settings.twitter_api_secret,
            resource_owner_key=settings.twitter_access_token,
            resource_owner_secret=settings.twitter_access_token_secret
        )
        
        chunk_size = 5 * 1024 * 1024  # 5 MB chunks
        segment_index = 0
        
        with open(video_path, 'rb') as video_file:
            while True:
                chunk = video_file.read(chunk_size)
                if not chunk:
                    break
                
                try:
                    response = oauth.post(
                        "https://upload.twitter.com/1.1/media/upload.json",
                        data={
                            "command": "APPEND",
                            "media_id": media_id,
                            "segment_index": segment_index,
                        },
                        files={"media": chunk}
                    )
                    response.raise_for_status()
                    segment_index += 1
                except requests.exceptions.HTTPError as e:
                    error_text = e.response.text if hasattr(e.response, 'text') else str(e)
                    raise PlatformAPIError(
                        f"Twitter upload APPEND failed at segment {segment_index}: {error_text}",
                        self.platform_name,
                        status_code=e.response.status_code if hasattr(e, 'response') else None
                    )
                except Exception as e:
                    raise PlatformAPIError(
                        f"Twitter upload APPEND failed at segment {segment_index}: {str(e)}",
                        self.platform_name
                    )
    
    async def _finalize_upload(self, media_id: str, access_token: str):
        """Finalize the upload using OAuth 1.0a."""
        from src.config import get_settings
        settings = get_settings()
        
        # Use OAuth 1.0a for media upload
        oauth = OAuth1Session(
            settings.twitter_api_key,
            client_secret=settings.twitter_api_secret,
            resource_owner_key=settings.twitter_access_token,
            resource_owner_secret=settings.twitter_access_token_secret
        )
        
        try:
            response = oauth.post(
                "https://upload.twitter.com/1.1/media/upload.json",
                data={
                    "command": "FINALIZE",
                    "media_id": media_id,
                }
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            error_text = e.response.text if hasattr(e.response, 'text') else str(e)
            raise PlatformAPIError(
                f"Twitter upload FINALIZE failed: {error_text}",
                self.platform_name,
                status_code=e.response.status_code if hasattr(e, 'response') else None
            )
        except Exception as e:
            raise PlatformAPIError(
                f"Twitter upload FINALIZE failed: {str(e)}",
                self.platform_name
            )
    
    async def _wait_for_processing(self, media_id: str, access_token: str, max_wait: int = 300):
        """Wait for Twitter to process the video using OAuth 1.0a."""
        import asyncio
        from src.config import get_settings
        settings = get_settings()
        
        # Use OAuth 1.0a for media upload
        oauth = OAuth1Session(
            settings.twitter_api_key,
            client_secret=settings.twitter_api_secret,
            resource_owner_key=settings.twitter_access_token,
            resource_owner_secret=settings.twitter_access_token_secret
        )
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                response = oauth.get(
                    "https://upload.twitter.com/1.1/media/upload.json",
                    params={
                        "command": "STATUS",
                        "media_id": media_id,
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                processing_info = data.get("processing_info")
                if not processing_info:
                    # No processing needed
                    return
                
                state = processing_info.get("state")
                if state == "succeeded":
                    return
                elif state == "failed":
                    error = processing_info.get("error", {})
                    raise PlatformAPIError(
                        f"Twitter video processing failed: {error.get('message', 'Unknown error')}",
                        self.platform_name
                    )
                
                # Wait before checking again
                check_after = processing_info.get("check_after_secs", 5)
                await asyncio.sleep(check_after)
                
            except requests.exceptions.HTTPError as e:
                error_text = e.response.text if hasattr(e.response, 'text') else str(e)
                raise PlatformAPIError(
                    f"Twitter processing status check failed: {error_text}",
                    self.platform_name,
                    status_code=e.response.status_code if hasattr(e, 'response') else None
                )
            except Exception as e:
                raise PlatformAPIError(
                    f"Twitter processing status check failed: {str(e)}",
                    self.platform_name
                )
        
        raise PlatformAPIError(
            f"Twitter video processing timeout after {max_wait} seconds",
            self.platform_name
        )
    
    async def _create_tweet(self, media_id: str, metadata: PostMetadata, access_token: str) -> dict:
        """Create tweet with uploaded video."""
        # Build tweet text with caption and hashtags
        tweet_text = metadata.caption
        if metadata.hashtags:
            hashtag_text = " ".join(f"#{tag.lstrip('#')}" for tag in metadata.hashtags)
            tweet_text = f"{tweet_text} {hashtag_text}".strip()
        
        # Ensure tweet doesn't exceed 280 characters
        if len(tweet_text) > 280:
            tweet_text = tweet_text[:277] + "..."
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.BASE_URL}/tweets",
                    json={
                        "text": tweet_text,
                        "media": {
                            "media_ids": [media_id]
                        }
                    },
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
                return response.json()["data"]
            except httpx.HTTPStatusError as e:
                raise PlatformAPIError(
                    f"Twitter tweet creation failed: {e.response.text}",
                    self.platform_name,
                    status_code=e.response.status_code
                )
    
    async def get_video_analytics(
        self,
        platform_post_id: str,
        access_token: str
    ) -> VideoAnalytics:
        """
        Fetch tweet metrics from Twitter API.
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/tweets/{platform_post_id}",
                    params={
                        "tweet.fields": "public_metrics"
                    },
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
                data = response.json()["data"]
                metrics = data.get("public_metrics", {})
                
                return VideoAnalytics(
                    views=metrics.get("impression_count", 0),
                    likes=metrics.get("like_count", 0),
                    comments=metrics.get("reply_count", 0),
                    shares=metrics.get("retweet_count", 0),
                    additional_metrics={
                        "quote_count": metrics.get("quote_count", 0),
                    }
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    raise PlatformRateLimitError(
                        "Twitter rate limit exceeded",
                        self.platform_name,
                        retry_after=int(e.response.headers.get("x-rate-limit-reset", 900))
                    )
                raise PlatformAPIError(
                    f"Failed to fetch Twitter analytics: {e.response.text}",
                    self.platform_name,
                    status_code=e.response.status_code
                )
    
    def validate_video(self, video: Video) -> ValidationResult:
        """Validate video against Twitter requirements."""
        errors = []
        warnings = []
        limits = self.get_platform_limits()
        
        # Check duration
        if video.duration > limits.max_video_duration:
            errors.append(f"Video duration ({video.duration}s) exceeds maximum ({limits.max_video_duration}s)")
        if video.duration < limits.min_video_duration:
            errors.append(f"Video duration ({video.duration}s) is below minimum ({limits.min_video_duration}s)")
        
        # Check file size
        if video.file_size > limits.max_file_size:
            errors.append(f"File size ({video.file_size} bytes) exceeds maximum ({limits.max_file_size} bytes)")
        
        # Check format
        if video.format.lower() not in limits.supported_formats:
            errors.append(f"Format {video.format} not supported. Supported: {', '.join(limits.supported_formats)}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def get_platform_limits(self) -> PlatformLimits:
        """Return Twitter platform limits."""
        return PlatformLimits(
            max_caption_length=280,
            max_hashtags=10,
            max_video_duration=140,  # 2 minutes 20 seconds
            min_video_duration=1,
            max_file_size=512 * 1024 * 1024,  # 512 MB
            supported_formats=["mp4", "mov"],
            supported_resolutions=["1920x1080", "1280x720", "720x1280", "1080x1920"],
            aspect_ratios=["16:9", "9:16", "1:1"]
        )
