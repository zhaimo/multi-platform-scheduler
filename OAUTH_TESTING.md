# OAuth Testing Guide

## YouTube OAuth Setup Complete! 🎉

The platform OAuth endpoints are now implemented and ready to test.

## What's Been Implemented

1. **Platform OAuth API** (`/api/auth/platforms`)
   - `GET /{platform}/authorize` - Initiate OAuth flow
   - `GET /{platform}/callback` - Handle OAuth callback
   - `GET /{platform}/disconnect` - Disconnect platform
   - `GET /status` - Get connection status for all platforms

2. **Database Model**
   - `PlatformConnection` table to store OAuth tokens
   - Relationships with User model
   - Migration applied successfully

3. **YouTube Adapter OAuth Methods**
   - `get_authorization_url()` - Generate OAuth URL
   - `exchange_code_for_tokens()` - Exchange code for tokens
   - `get_user_info()` - Get YouTube channel info

## Testing the OAuth Flow

### Step 1: Update Google Cloud Console

You need to add the backend redirect URI to your Google Cloud Console:

1. Go to https://console.cloud.google.com/apis/credentials
2. Click on your OAuth 2.0 Client ID
3. Add this to "Authorized redirect URIs":
   ```
   http://localhost:8000/api/auth/platforms/youtube/callback
   ```
4. Click "Save"

### Step 2: Test the OAuth Flow

1. **Login to the app**
   - Go to http://localhost:3000
   - Login with your account (email: zhaimo@yahoo.com)

2. **Navigate to Platforms page**
   - Go to http://localhost:3000/dashboard/platforms
   - You should see YouTube, TikTok, Instagram, and Facebook

3. **Connect YouTube**
   - Click "Connect" on YouTube
   - The frontend will call `/api/auth/platforms/youtube/authorize`
   - You'll get an authorization URL and be redirected to Google OAuth
   - Grant permissions to your YouTube channel
   - You'll be redirected back to: `http://localhost:8000/api/auth/platforms/youtube/callback`
   - The backend will exchange the code for tokens and save them
   - You'll be redirected to the platforms page with success message

4. **Verify Connection**
   - The YouTube card should now show "Connected"
   - Your channel name should be displayed

### Troubleshooting Connection Issues

If you see "Failed to connect to YouTube", check:

1. **Backend logs**:
   ```bash
   tail -f logs/backend.log | grep -i "youtube\|error"
   ```

2. **Browser console** (F12):
   - Check for any JavaScript errors
   - Look at the Network tab for failed API calls

3. **Common issues**:
   - **401 Unauthorized**: Your JWT token expired, try logging out and back in
   - **redirect_uri_mismatch**: The redirect URI in Google Console doesn't match
   - **invalid_state**: CSRF token issue, try clearing cookies and logging in again
   - **Connection timeout**: Backend might not be running, check `./status.sh`

### Step 3: Test Video Upload

Once YouTube is connected, you can test the full posting flow:

1. **Upload a video**
   - Go to Videos page
   - Upload a short video (< 60 seconds for YouTube Shorts)

2. **Create a post**
   - Go to Posts → New Post
   - Select your uploaded video
   - Select YouTube as platform
   - Add title and description
   - Click "Post Now" or "Schedule"

3. **Check the post**
   - The system will use your stored OAuth tokens
   - Video will be uploaded to YouTube as a Short
   - Check your YouTube channel to verify

## API Endpoints

### Get Platform Status
```bash
curl -X GET http://localhost:8000/api/auth/platforms/status \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Initiate YouTube OAuth
```bash
# This will redirect to Google OAuth
curl -X GET http://localhost:8000/api/auth/platforms/youtube/authorize \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Disconnect YouTube
```bash
curl -X GET http://localhost:8000/api/auth/platforms/youtube/disconnect \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Configuration

Current configuration in `.env`:
```
YOUTUBE_CLIENT_ID=your-client-id.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=your-client-secret
YOUTUBE_REDIRECT_URI=http://localhost:8000/api/auth/platforms/youtube/callback
FRONTEND_URL=http://localhost:3000
```

## Troubleshooting

### "redirect_uri_mismatch" error
- Make sure you added `http://localhost:8000/api/auth/platforms/youtube/callback` to Google Cloud Console
- Check that the URI matches exactly (no trailing slash)

### "invalid_state" error
- This is a CSRF protection error
- Try clearing cookies and logging in again
- Make sure you're using the same browser session

### "connection_failed" error
- Check backend logs: `tail -f logs/backend.log`
- Verify your YouTube credentials are correct
- Make sure the database migration ran successfully

### Token not working for uploads
- Check if token is expired
- Verify scopes include `youtube.upload`
- Try disconnecting and reconnecting

## Next Steps

1. Test the OAuth flow with YouTube
2. Upload a test video and post to YouTube
3. Verify the video appears on your YouTube channel
4. Implement similar OAuth flows for TikTok, Instagram, and Facebook

## Notes

- OAuth tokens are stored encrypted in the database
- Refresh tokens are used to automatically renew expired access tokens
- The system handles token refresh automatically during uploads
- Platform connections are user-specific (each user has their own connections)
