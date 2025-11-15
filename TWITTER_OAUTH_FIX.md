# Twitter OAuth 1.0a Credentials Issue

## Problem
Posts to Twitter are stuck in "PROCESSING" status because the OAuth 1.0a credentials in the `.env` file are invalid or expired.

Twitter requires **two types of authentication**:
1. **OAuth 2.0** - For user authentication (stored in database when you "Connect Twitter")
2. **OAuth 1.0a** - For media uploads (stored in `.env` file)

When you reconnect Twitter in the UI, you only update the OAuth 2.0 token, but the OAuth 1.0a credentials remain invalid.

## Solution

You need to generate new OAuth 1.0a credentials from the Twitter Developer Portal:

### Step 1: Go to Twitter Developer Portal
1. Visit https://developer.twitter.com/en/portal/dashboard
2. Select your app
3. Go to "Keys and tokens" tab

### Step 2: Generate OAuth 1.0a Credentials
1. Under "Authentication Tokens" section, find "Access Token and Secret"
2. Click "Generate" or "Regenerate" to create new tokens
3. Copy the following values:
   - **API Key** (Consumer Key)
   - **API Key Secret** (Consumer Secret)
   - **Access Token**
   - **Access Token Secret**

### Step 3: Update .env File
Update these values in `backend/.env`:

```bash
# OAuth 1.0a credentials (for media uploads)
TWITTER_API_KEY=your_api_key_here
TWITTER_API_SECRET=your_api_secret_here
TWITTER_ACCESS_TOKEN=your_access_token_here
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret_here
```

### Step 4: Restart Services
```bash
docker-compose restart backend celery-worker
```

### Step 5: Test the Credentials
```bash
docker-compose exec backend python test_twitter_oauth.py
```

You should see:
```
✅ OAuth 1.0a credentials are VALID
   Authenticated as: @your_twitter_handle
```

### Step 6: Try Posting Again
Once the credentials are valid, try posting a video to Twitter again.

## Important Notes

- The OAuth 1.0a tokens are **app-level** tokens, not user-level
- They don't expire unless you regenerate them
- Make sure your Twitter app has "Read and Write" permissions
- The app must also have "Elevated" access for media uploads

## Current Status
❌ OAuth 1.0a credentials are INVALID - need to be regenerated from Twitter Developer Portal
