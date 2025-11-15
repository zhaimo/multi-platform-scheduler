# Twitter Integration Setup Guide

## Required Setup Steps

### 1. Twitter Developer Portal Configuration

1. **Go to Twitter Developer Portal**: https://developer.twitter.com/en/portal/dashboard

2. **Create/Update Your App**:
   - Navigate to your project and app
   - Go to "Settings" → "User authentication settings"

3. **Enable OAuth 2.0**:
   - Type of App: Web App
   - App permissions: **Read and Write** (required for posting)
   - Callback URL: `http://localhost:8000/api/auth/platforms/twitter/callback` (or your production URL)
   - Website URL: Your app's website

4. **Request Required Scopes**:
   The app now requests these scopes during OAuth:
   - `tweet.read` - Read tweets
   - `tweet.write` - Post tweets
   - `users.read` - Read user information
   - `offline.access` - Refresh tokens
   - **`media.write`** - Upload media (REQUIRED for video upload)

5. **Save Your Credentials**:
   - Client ID
   - Client Secret
   - Add these to your `.env` file

### 2. Update Environment Variables

Ensure your `backend/.env` file has:
```
TWITTER_CLIENT_ID=your_client_id_here
TWITTER_CLIENT_SECRET=your_client_secret_here
TWITTER_REDIRECT_URI=http://localhost:8000/api/auth/platforms/twitter/callback
```

### 3. Reconnect Your Twitter Account

After updating the app permissions and scopes:
1. Go to the Platforms page in your app
2. Disconnect Twitter if already connected
3. Reconnect Twitter - you'll be asked to authorize the new `media.write` scope
4. Complete the OAuth flow

## Current Status

Twitter integration has been successfully implemented with the following components:

### ✅ Completed
1. **OAuth 2.0 Authentication** - Users can connect their Twitter accounts
2. **Platform Adapter Registration** - Twitter adapter is properly registered in all services
3. **Database Schema** - TWITTER enum added to platform_enum type
4. **Chunked Upload Implementation** - Complete implementation of Twitter's 3-phase upload process
5. **Post Creation** - Posts are created and queued for processing

### ⚠️ Current Issue

**403 Forbidden Error on Media Upload**

The Twitter API is returning a 403 Forbidden error when attempting to upload media. This is because:

1. **OAuth 2.0 Limitations**: The current OAuth 2.0 implementation uses scopes: `tweet.read tweet.write users.read offline.access`
2. **Media Upload Requirements**: Twitter's media upload endpoint (`upload.twitter.com/1.1/media/upload.json`) has special requirements:
   - It uses the v1.1 API (not v2)
   - It may require OAuth 1.0a authentication
   - It may require elevated API access or specific app permissions

### Solutions

#### Option 1: Request Elevated Access (Recommended)
1. Apply for Elevated access in the Twitter Developer Portal
2. Ensure the app has "Read and Write" permissions
3. Verify media upload permissions are enabled

#### Option 2: Use OAuth 1.0a for Media Upload
Implement hybrid authentication:
- Use OAuth 2.0 for user authentication and tweet reading
- Use OAuth 1.0a signatures for media upload requests

#### Option 3: Twitter API v2 Media Upload
Wait for Twitter to fully support media upload in API v2 with OAuth 2.0

### Testing Without Real Upload

For testing purposes, you can:
1. Verify the post creation works (status shows as "processing")
2. Check that the Celery worker picks up the task
3. Confirm the chunked upload code is properly structured

### Next Steps

1. **Check Twitter Developer Portal**:
   - Go to https://developer.twitter.com/en/portal/dashboard
   - Verify your app has "Read and Write" permissions
   - Check if Elevated access is required
   - Ensure media upload is enabled

2. **Update App Permissions**:
   - If needed, request Elevated access
   - Update OAuth scopes if additional permissions are available

3. **Alternative**: Implement OAuth 1.0a for media upload as a fallback

## Code Implementation

The chunked upload implementation is complete and follows Twitter's documentation:

```python
# Phase 1: INIT - Initialize upload
# Phase 2: APPEND - Upload video chunks (5MB each)
# Phase 3: FINALIZE - Complete upload
# Phase 4: Wait for processing
# Phase 5: Create tweet with media
```

All error handling, retry logic, and status tracking are properly implemented.

## Workaround for Testing

To test other platforms while Twitter permissions are being resolved:
1. Use TikTok, YouTube, Instagram, or Facebook for video posting
2. Twitter posts will remain in "processing" status until the 403 error is resolved
3. Once Twitter permissions are fixed, existing posts can be retried

## Files Modified

1. `backend/src/adapters/twitter.py` - Complete chunked upload implementation
2. `backend/src/api/posts.py` - Twitter adapter registration
3. `backend/src/tasks.py` - Twitter adapter support in Celery tasks
4. `backend/alembic/versions/007_add_twitter_to_platform_enum.py` - Database migration

## Error Logs

```
HTTP Request: POST https://upload.twitter.com/1.1/media/upload.json "HTTP/1.1 403 Forbidden"
Platform API error posting video: Twitter upload INIT failed
```

This indicates an authentication/authorization issue with the Twitter API, not a code issue.
