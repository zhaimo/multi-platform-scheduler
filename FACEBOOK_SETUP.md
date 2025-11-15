# Facebook Integration Setup Guide

This guide will help you set up Facebook video posting for your multi-platform scheduler.

## Prerequisites

- A Facebook account
- Access to Meta for Developers (https://developers.facebook.com)

## Step 1: Create a Facebook App

1. Go to https://developers.facebook.com
2. Click "My Apps" in the top right
3. Click "Create App"
4. Select "Consumer" as the app type
5. Fill in the details:
   - App Name: "Multi-Platform Video Scheduler" (or your preferred name)
   - App Contact Email: Your email
6. Click "Create App"

## Step 2: Add Facebook Login Product

1. In your app dashboard, find "Facebook Login" in the products list
2. Click "Set Up" on Facebook Login
3. Select "Web" as the platform
4. Enter your site URL: `http://localhost:3000` (for development)
5. Click "Save" and "Continue"

## Step 3: Configure OAuth Settings

1. In the left sidebar, go to "Facebook Login" → "Settings"
2. Add these to "Valid OAuth Redirect URIs":
   ```
   http://localhost:3000/dashboard/platforms/callback
   ```
3. For production, also add:
   ```
   https://yourdomain.com/dashboard/platforms/callback
   ```
4. Click "Save Changes"

## Step 4: Get Your App Credentials

1. In the left sidebar, go to "Settings" → "Basic"
2. Copy your "App ID"
3. Click "Show" next to "App Secret" and copy it
4. Save these credentials - you'll need them next

## Step 5: Request Permissions

For video posting, you need these permissions:
- `pages_show_list` - To list your Facebook Pages
- `pages_read_engagement` - To read page data
- `pages_manage_posts` - To create posts on pages
- `publish_video` - To upload videos

Note: Some permissions require App Review by Facebook. For development/testing:
1. Add yourself as a test user or developer
2. You can use the app without review

## Step 6: Add Environment Variables

Add these to your `.env` file in the `multi-platform-scheduler` directory:

```bash
# Facebook OAuth
FACEBOOK_CLIENT_ID=your_app_id_here
FACEBOOK_CLIENT_SECRET=your_app_secret_here
FACEBOOK_REDIRECT_URI=http://localhost:3000/dashboard/platforms/callback
```

Replace `your_app_id_here` and `your_app_secret_here` with the credentials from Step 4.

## Step 7: Restart Your Application

```bash
cd multi-platform-scheduler
docker-compose restart backend
```

## Step 8: Connect Facebook

1. Go to http://localhost:3000/dashboard/platforms
2. Click "Connect" next to Facebook
3. Log in with your Facebook account
4. Authorize the requested permissions
5. You'll be redirected back to your app

## Testing

1. Go to the Videos page
2. Select a video
3. Click "Post"
4. Select Facebook as the platform
5. Add a caption and click "Post Now"
6. Check your Facebook profile/page for the posted video

## Troubleshooting

### "App Not Set Up" Error
- Make sure you've added Facebook Login product
- Check that OAuth redirect URIs are configured correctly

### "Permission Denied" Error
- Ensure you've requested the necessary permissions
- For pages, make sure you're an admin of the page

### "Invalid OAuth Redirect URI"
- Double-check the redirect URI in Facebook app settings matches exactly
- Include the protocol (http:// or https://)

### Video Upload Fails
- Check video format (MP4 recommended)
- Ensure video size is under Facebook's limits (4GB)
- Verify you have `publish_video` permission

## Facebook Video Requirements

- Format: MP4, MOV
- Max size: 4GB
- Max length: 240 minutes
- Recommended aspect ratio: 16:9 or 9:16 (vertical)
- Min resolution: 600x600

## Next Steps

Once Facebook is working, you can:
- Post to Facebook Pages (requires page admin access)
- Schedule posts for later
- Post the same video to multiple platforms simultaneously

## Useful Links

- [Facebook Graph API Documentation](https://developers.facebook.com/docs/graph-api)
- [Video API Reference](https://developers.facebook.com/docs/video-api)
- [App Review Process](https://developers.facebook.com/docs/app-review)
