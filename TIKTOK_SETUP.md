# TikTok Integration Setup Guide

This guide will help you set up TikTok video posting for your multi-platform scheduler.

## Important Notes

⚠️ **TikTok Developer Access**: TikTok requires manual approval for API access, which can take 1-3 business days.

⚠️ **Business Account**: You'll need a TikTok Business account to use the API.

## Prerequisites

- A TikTok account
- Willingness to wait for API approval (1-3 days)

## Step 1: Apply for TikTok Developer Access

1. Go to https://developers.tiktok.com
2. Click "Register" or "Login" in the top right
3. Log in with your TikTok account
4. Complete the developer registration form:
   - Select "Individual" or "Company"
   - Provide your contact information
   - Describe your use case: "Multi-platform video scheduling tool"
5. Submit and wait for approval email (usually 1-3 business days)

## Step 2: Create a TikTok App (After Approval)

1. Once approved, log in to https://developers.tiktok.com
2. Click "Manage apps" in the dashboard
3. Click "+ Add app"
4. Fill in the app details:
   - App name: "Multi-Platform Video Scheduler"
   - Category: "Social Media Management"
   - Description: "A tool for scheduling and posting videos across multiple platforms"
5. Click "Submit"

## Step 3: Configure Your App

1. In your app dashboard, go to "Basic information"
2. Add your redirect URI:
   ```
   http://localhost:3000/dashboard/platforms/callback
   ```
3. For production, also add:
   ```
   https://yourdomain.com/dashboard/platforms/callback
   ```
4. Save changes

## Step 4: Request API Permissions

You need to request these scopes:
- `user.info.basic` - Get user profile information
- `video.upload` - Upload videos
- `video.publish` - Publish videos

1. In your app dashboard, go to "Products"
2. Find "Login Kit" and click "Apply"
3. Request the scopes listed above
4. Provide justification for each scope
5. Submit for review (may take additional time)

## Step 5: Get Your Credentials

1. In your app dashboard, go to "Basic information"
2. Copy your "Client Key" (this is your Client ID)
3. Copy your "Client Secret"
4. Save these credentials securely

## Step 6: Add Environment Variables

Add these to your `.env` file in the `multi-platform-scheduler` directory:

```bash
# TikTok OAuth
TIKTOK_CLIENT_ID=your_client_key_here
TIKTOK_CLIENT_SECRET=your_client_secret_here
TIKTOK_REDIRECT_URI=http://localhost:3000/dashboard/platforms/callback
```

Replace `your_client_key_here` and `your_client_secret_here` with your actual credentials.

## Step 7: Restart Your Application

```bash
cd multi-platform-scheduler
docker-compose restart backend
```

## Step 8: Connect TikTok

1. Go to http://localhost:3000/dashboard/platforms
2. Click "Connect" next to TikTok
3. Log in with your TikTok account
4. Authorize the requested permissions
5. You'll be redirected back to your app

## Testing

1. Go to the Videos page
2. Select a video
3. Click "Post"
4. Select TikTok as the platform
5. Add a caption and hashtags
6. Click "Post Now"
7. Check your TikTok profile for the posted video

## TikTok Video Requirements

- Format: MP4, MOV, MPEG, AVI, WMV, 3GP, WEBM
- Max size: 287.6 MB
- Max length: 10 minutes (60 seconds for regular users, up to 10 min for verified)
- Min length: 3 seconds
- Recommended aspect ratio: 9:16 (vertical)
- Min resolution: 720x1280
- Max resolution: 1080x1920

## Troubleshooting

### "Developer Access Pending"
- TikTok approval can take 1-3 business days
- Check your email for approval notification
- You cannot proceed until approved

### "Invalid Client Key"
- Double-check your Client Key and Client Secret
- Make sure there are no extra spaces
- Verify the credentials in TikTok Developer Portal

### "Redirect URI Mismatch"
- Ensure the redirect URI in TikTok app settings matches exactly
- Include the protocol (http:// or https://)
- No trailing slashes

### "Insufficient Permissions"
- Make sure you've requested and been approved for video.upload and video.publish scopes
- Some scopes require additional review by TikTok

### Video Upload Fails
- Check video format and size limits
- Ensure video meets TikTok's content guidelines
- Verify your account is in good standing

## Alternative: TikTok for Business

If you're having trouble with the regular API:

1. Consider TikTok for Business API
2. More reliable but requires business verification
3. Better for commercial use
4. Visit: https://business-api.tiktok.com

## Timeline Expectations

- Developer registration approval: 1-3 business days
- App creation: Immediate after approval
- Scope approval: 1-5 business days
- Total time: 2-8 business days typically

## Useful Links

- [TikTok Developer Portal](https://developers.tiktok.com)
- [TikTok API Documentation](https://developers.tiktok.com/doc)
- [Content Posting API](https://developers.tiktok.com/doc/content-posting-api-get-started)
- [Login Kit Documentation](https://developers.tiktok.com/doc/login-kit-web)

## Next Steps

While waiting for TikTok approval, you can:
- Set up Facebook (faster approval)
- Test with YouTube (already working)
- Prepare your video content
- Familiarize yourself with TikTok's content policies
