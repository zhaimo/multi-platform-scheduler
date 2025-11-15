# YouTube API Setup - Quick Guide

Follow these steps to set up YouTube API credentials for testing.

## Step 1: Go to Google Cloud Console

1. Open https://console.cloud.google.com/
2. Sign in with your Google account

## Step 2: Create a New Project

1. Click the project dropdown at the top (next to "Google Cloud")
2. Click "NEW PROJECT"
3. Enter project name: **"Video Scheduler"**
4. Click "CREATE"
5. Wait for the project to be created (takes a few seconds)
6. Select the new project from the dropdown

## Step 3: Enable YouTube Data API v3

1. In the left sidebar, go to **"APIs & Services"** → **"Library"**
2. Search for **"YouTube Data API v3"**
3. Click on it
4. Click **"ENABLE"**
5. Wait for it to enable

## Step 4: Configure OAuth Consent Screen

1. Go to **"APIs & Services"** → **"OAuth consent screen"**
2. Select **"External"** user type
3. Click **"CREATE"**

### Fill in the form:
- **App name**: Video Scheduler
- **User support email**: [your email]
- **Developer contact email**: [your email]
- Leave other fields as default
4. Click **"SAVE AND CONTINUE"**

### Scopes page:
5. Click **"ADD OR REMOVE SCOPES"**
6. Search for and select:
   - `../auth/youtube.upload`
   - `../auth/youtube.force-ssl`
7. Click **"UPDATE"**
8. Click **"SAVE AND CONTINUE"**

### Test users page:
9. Click **"+ ADD USERS"**
10. Enter your Google email address
11. Click **"ADD"**
12. Click **"SAVE AND CONTINUE"**
13. Click **"BACK TO DASHBOARD"**

## Step 5: Create OAuth 2.0 Credentials

1. Go to **"APIs & Services"** → **"Credentials"**
2. Click **"+ CREATE CREDENTIALS"** at the top
3. Select **"OAuth 2.0 Client ID"**

### Configure the OAuth client:
4. Application type: **"Web application"**
5. Name: **"Video Scheduler Web Client"**

### Authorized redirect URIs:
6. Click **"+ ADD URI"**
7. Enter: `http://localhost:3000/dashboard/platforms/callback`
8. Click **"CREATE"**

## Step 6: Copy Your Credentials

A popup will appear with your credentials:
1. **Copy the Client ID** (looks like: `xxxxx.apps.googleusercontent.com`)
2. **Copy the Client Secret** (looks like: `GOCSPX-xxxxx`)
3. Click **"OK"**

## Step 7: Update Your .env File

1. Open `multi-platform-scheduler/backend/.env`
2. Find these lines:
```bash
YOUTUBE_CLIENT_ID=your-youtube-client-id
YOUTUBE_CLIENT_SECRET=your-youtube-client-secret
```

3. Replace with your actual credentials:
```bash
YOUTUBE_CLIENT_ID=xxxxx.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=GOCSPX-xxxxx
```

4. Save the file

## Step 8: Restart the Backend

```bash
cd multi-platform-scheduler
./stop.sh
./start.sh
```

## Step 9: Test the Connection

1. Go to http://localhost:3000/dashboard/platforms
2. Click **"Connect"** under YouTube
3. You should be redirected to Google's OAuth page
4. Sign in with your Google account (the one you added as a test user)
5. Click **"Allow"** to grant permissions
6. You should be redirected back to your app
7. YouTube should now show as **"Connected"**

## Troubleshooting

### "Access blocked: This app's request is invalid"
- Make sure you added your email as a test user in Step 4
- Verify the redirect URI matches exactly: `http://localhost:3000/dashboard/platforms/callback`

### "The OAuth client was not found"
- Double-check you copied the Client ID correctly
- Make sure there are no extra spaces in the `.env` file
- Restart the backend after updating `.env`

### "Redirect URI mismatch"
- Go back to Google Cloud Console → Credentials
- Click on your OAuth client
- Verify the redirect URI is: `http://localhost:3000/dashboard/platforms/callback`
- No trailing slash!

### Still not working?
Check the backend logs:
```bash
tail -f multi-platform-scheduler/logs/backend.log
```

## What's Next?

Once YouTube is connected, you can:
1. Upload a video in the Videos page
2. Go to Posts → New Post
3. Select your video
4. Select YouTube as the platform
5. Enter a title and description
6. Click "Create Post"
7. Check your YouTube channel - the video should appear as a Short!

---

## Important Notes

- **Publishing Status**: Your app is in "Testing" mode, which means only test users can use it
- **Quota Limits**: YouTube API has daily quota limits (10,000 units/day for free tier)
- **Video Requirements**: For YouTube Shorts, videos should be:
  - Vertical (9:16 aspect ratio)
  - Under 60 seconds
  - Resolution: 1080x1920 or higher

- **Going Live**: To make your app available to all users, you'll need to submit it for verification (takes 1-2 weeks)

---

## Quick Reference

**Google Cloud Console**: https://console.cloud.google.com/
**YouTube API Docs**: https://developers.google.com/youtube/v3
**OAuth Scopes**: https://developers.google.com/youtube/v3/guides/auth/server-side-web-apps

**Your Project**: Video Scheduler
**Redirect URI**: `http://localhost:3000/dashboard/platforms/callback`
