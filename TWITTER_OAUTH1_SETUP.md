# Twitter OAuth 1.0a Setup for Video Uploads

## Why OAuth 1.0a is Needed

Twitter's media upload API (`/1.1/media/upload.json`) requires OAuth 1.0a authentication. While we use OAuth 2.0 for user authentication, we need OAuth 1.0a credentials for uploading videos.

## Getting OAuth 1.0a Credentials

### Step 1: Go to Twitter Developer Portal

1. Visit [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Select your app (the same one you're using for OAuth 2.0)

### Step 2: Get API Keys

1. Go to your app's "Keys and tokens" tab
2. You'll see two sections:
   - **API Key and Secret** (OAuth 1.0a)
   - **Client ID and Client Secret** (OAuth 2.0)

### Step 3: Generate Access Token and Secret

1. Scroll down to "Authentication Tokens"
2. Click "Generate" under "Access Token and Secret"
3. **IMPORTANT**: Save these immediately - you won't be able to see the secret again!
4. You'll get:
   - Access Token
   - Access Token Secret

### Step 4: Update Your .env File

Add these four values to your `.env` file:

```bash
# OAuth 1.0a credentials (for media uploads)
TWITTER_API_KEY=your-api-key-here
TWITTER_API_SECRET=your-api-secret-here
TWITTER_ACCESS_TOKEN=your-access-token-here
TWITTER_ACCESS_TOKEN_SECRET=your-access-token-secret-here
```

### Step 5: Restart Services

```bash
docker-compose restart backend celery-worker
```

## Important Notes

### App-Level vs User-Level Tokens

The OAuth 1.0a Access Token and Secret you generate are **app-level** credentials. This means:
- They authenticate your application, not individual users
- All video uploads will be posted from the Twitter account that owns the app
- This is different from OAuth 2.0, which authenticates individual users

### Security Considerations

- **Never commit these credentials to Git**
- Keep them in your `.env` file (which should be in `.gitignore`)
- Treat them like passwords - they give full access to your Twitter account

### Permissions

Make sure your Twitter app has:
- ✅ Read and Write permissions
- ✅ OAuth 1.0a enabled
- ✅ OAuth 2.0 enabled

## Testing

After setup, try posting a video to Twitter:

1. Connect your Twitter account (OAuth 2.0)
2. Upload a video
3. Create a post with Twitter selected
4. The video should upload successfully!

## Troubleshooting

### "Twitter OAuth 1.0a credentials not configured"

- Make sure all four environment variables are set in `.env`
- Restart the backend and worker containers
- Check that the values don't have extra spaces or quotes

### "401 Unauthorized"

- Your API Key or Secret is incorrect
- Regenerate the credentials in the Twitter Developer Portal
- Update your `.env` file

### "403 Forbidden"

- Your app doesn't have Read and Write permissions
- Go to your app settings and change permissions to "Read and Write"
- Regenerate your Access Token and Secret after changing permissions

### "Media upload still failing"

- Check the worker logs: `docker-compose logs celery-worker --tail=100`
- Look for specific error messages
- Verify all four OAuth 1.0a credentials are correct

## Alternative: User-Level Authentication (Advanced)

If you want each user to upload videos from their own account (not the app owner's account), you would need to:

1. Implement a full OAuth 1.0a flow for each user
2. Store OAuth 1.0a tokens per user in the database
3. Use those tokens for media uploads

This is more complex and beyond the current implementation. The current approach (app-level tokens) is simpler and works well for most use cases.
