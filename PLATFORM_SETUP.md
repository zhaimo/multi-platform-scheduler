# Platform API Setup Guide

Before testing platform connections, you need to set up API credentials for at least one platform.

## Quick Start - Choose One Platform

Pick the easiest platform for you to set up:
- **TikTok**: Good for testing, requires TikTok Developer account
- **YouTube**: Requires Google Cloud Console setup
- **Instagram**: Requires Facebook Developer account + Instagram Business account
- **Facebook**: Requires Facebook Developer account

---

## Option 1: TikTok Setup (Recommended for Testing)

### Step 1: Create TikTok Developer Account
1. Go to https://developers.tiktok.com/
2. Sign up or log in with your TikTok account
3. Complete the developer registration

### Step 2: Create an App
1. Go to "My Apps" in the developer portal
2. Click "Create App"
3. Fill in app details:
   - App Name: "Video Scheduler Test"
   - App Type: "Web"
4. Submit for review (may take 1-2 days)

### Step 3: Get API Credentials
1. Once approved, go to your app dashboard
2. Find "Client Key" and "Client Secret"
3. Add these to your `.env` file:
```bash
TIKTOK_CLIENT_KEY=your-actual-client-key
TIKTOK_CLIENT_SECRET=your-actual-client-secret
```

### Step 4: Configure Redirect URI
1. In TikTok Developer Portal, go to app settings
2. Add redirect URI: `http://localhost:3000/dashboard/platforms/callback`
3. Save changes

### Step 5: Request Permissions
Make sure your app has these scopes:
- `user.info.basic`
- `video.upload`
- `video.publish`

---

## Option 2: YouTube Setup

### Step 1: Create Google Cloud Project
1. Go to https://console.cloud.google.com/
2. Create a new project: "Video Scheduler"
3. Enable YouTube Data API v3

### Step 2: Create OAuth Credentials
1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth 2.0 Client ID"
3. Configure OAuth consent screen:
   - User Type: External
   - App Name: "Video Scheduler"
   - Add your email
4. Create OAuth Client:
   - Application type: Web application
   - Authorized redirect URIs: `http://localhost:3000/dashboard/platforms/callback`

### Step 3: Get Credentials
1. Copy Client ID and Client Secret
2. Add to `.env`:
```bash
YOUTUBE_CLIENT_ID=your-client-id.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=your-client-secret
```

### Step 4: Add Test Users
1. In OAuth consent screen, add your Google account as a test user
2. This allows you to test while app is in development mode

---

## Option 3: Instagram Setup

### Step 1: Create Facebook App
1. Go to https://developers.facebook.com/
2. Create a new app
3. Select "Business" type

### Step 2: Add Instagram Product
1. In app dashboard, add "Instagram" product
2. Configure Instagram Basic Display

### Step 3: Get Credentials
1. Go to Instagram Basic Display settings
2. Create new Instagram App
3. Copy App ID and App Secret
4. Add to `.env`:
```bash
INSTAGRAM_CLIENT_ID=your-app-id
INSTAGRAM_CLIENT_SECRET=your-app-secret
```

### Step 4: Configure Redirect URI
Add: `http://localhost:3000/dashboard/platforms/callback`

### Step 5: Requirements
- You need an Instagram Business or Creator account
- Account must be linked to a Facebook Page

---

## Option 4: Facebook Setup

### Step 1: Create Facebook App
1. Go to https://developers.facebook.com/
2. Create new app (Business type)

### Step 2: Add Facebook Login
1. Add "Facebook Login" product
2. Configure settings

### Step 3: Get Credentials
1. Go to Settings → Basic
2. Copy App ID and App Secret
3. Add to `.env`:
```bash
FACEBOOK_APP_ID=your-app-id
FACEBOOK_APP_SECRET=your-app-secret
```

### Step 4: Configure Redirect URI
Add: `http://localhost:3000/dashboard/platforms/callback`

---

## Testing Without Real Platform APIs

If you want to test the app without setting up real platform APIs, you can:

### Option A: Mock Mode (Development)
Create a mock adapter for testing:

1. Edit `backend/src/config.py` and add:
```python
USE_MOCK_PLATFORMS = True  # Set to True for testing
```

2. This will simulate platform connections without real API calls

### Option B: Skip Platform Testing
You can test other features without platform connections:
- Video upload ✅
- Video library ✅
- User authentication ✅
- Templates ✅
- Scheduling (will fail at posting step)

---

## After Setup

Once you've configured at least one platform:

1. **Restart the backend** to load new credentials:
```bash
cd multi-platform-scheduler
./stop.sh
./start.sh
```

2. **Verify configuration**:
```bash
# Check if credentials are loaded
curl http://localhost:8000/health
```

3. **Start testing** using the TESTING_GUIDE.md

---

## Troubleshooting

### "Invalid client credentials" error
- Double-check Client ID/Secret are correct
- Ensure no extra spaces in `.env` file
- Restart backend after changing `.env`

### "Redirect URI mismatch" error
- Verify redirect URI in platform developer console matches exactly
- Should be: `http://localhost:3000/dashboard/platforms/callback`
- Check for trailing slashes

### "Insufficient permissions" error
- Ensure your app has requested the correct scopes/permissions
- For TikTok: `video.upload`, `video.publish`
- For YouTube: `youtube.upload`, `youtube.force-ssl`
- For Instagram: `instagram_basic`, `instagram_content_publish`
- For Facebook: `pages_manage_posts`, `pages_read_engagement`

### Platform API is in review/pending
- Most platforms require app review before going live
- You can usually test with your own account while in development mode
- Add your account as a test user in the platform developer console

---

## Quick Test Checklist

Before testing platform connections:
- [ ] Created developer account on chosen platform
- [ ] Created app in platform developer console
- [ ] Got Client ID/Key and Client Secret
- [ ] Added credentials to `backend/.env`
- [ ] Configured redirect URI in platform console
- [ ] Requested necessary permissions/scopes
- [ ] Restarted backend services
- [ ] Added yourself as test user (if required)

---

## Need Help?

If you're stuck on platform setup:
1. Check platform-specific documentation
2. Look for "Getting Started" guides in developer portals
3. Many platforms have sandbox/test modes for development
4. Consider starting with TikTok as it's often the simplest to set up
