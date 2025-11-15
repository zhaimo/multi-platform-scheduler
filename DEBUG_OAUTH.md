# Debug OAuth Connection Issues

## Quick Debugging Steps

### 1. Check if backend is receiving the request

Open a terminal and watch the backend logs in real-time:

```bash
cd multi-platform-scheduler
tail -f logs/backend.log
```

Then try to connect YouTube from the frontend. You should see log entries like:
```
INFO - Generated youtube OAuth URL for user <user_id>
```

If you don't see any logs, the frontend isn't calling the backend correctly.

### 2. Check browser console

1. Open the Platforms page: http://localhost:3000/dashboard/platforms
2. Open browser DevTools (F12 or Cmd+Option+I)
3. Go to the Console tab
4. Click "Connect" on YouTube
5. Look for any errors in red

Common errors:
- `401 Unauthorized` - Your session expired, logout and login again
- `Network Error` - Backend isn't running
- `CORS error` - Backend CORS configuration issue

### 3. Check Network tab

1. In DevTools, go to the Network tab
2. Click "Connect" on YouTube
3. Look for the request to `/api/auth/platforms/youtube/authorize`
4. Click on it to see:
   - Request headers (should include `Authorization: Bearer ...`)
   - Response status (should be 200)
   - Response body (should have `authorization_url`)

### 4. Test the API directly

Get your JWT token from the browser:
1. Open DevTools → Application → Local Storage
2. Find the key with your JWT token (usually `token` or `access_token`)
3. Copy the token value

Then test the API:

```bash
# Replace YOUR_TOKEN with the actual token
curl -X GET http://localhost:8000/api/auth/platforms/youtube/authorize \
  -H "Authorization: Bearer YOUR_TOKEN" \
  | python3 -m json.tool
```

Expected response:
```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?..."
}
```

### 5. Check Google Cloud Console

Make sure the redirect URI is configured:

1. Go to https://console.cloud.google.com/apis/credentials
2. Click on your OAuth 2.0 Client ID
3. Under "Authorized redirect URIs", you should see:
   ```
   http://localhost:8000/api/auth/platforms/youtube/callback
   ```
4. If not, add it and click "Save"

### 6. Test the full OAuth flow manually

1. Get the authorization URL from step 4 above
2. Copy the full URL
3. Open it in your browser
4. Grant permissions
5. You'll be redirected to the callback URL
6. Check if you see a success message or error

### 7. Check database connection

Verify the platform connection was saved:

```bash
cd backend
source venv/bin/activate
python3 -c "
import asyncio
from src.database import get_db
from src.models.database_models import PlatformConnection
from sqlalchemy import select

async def check_connections():
    async for db in get_db():
        result = await db.execute(select(PlatformConnection))
        connections = result.scalars().all()
        for conn in connections:
            print(f'Platform: {conn.platform}, User: {conn.user_id}, Active: {conn.is_active}')
        if not connections:
            print('No platform connections found')
        break

asyncio.run(check_connections())
"
```

## Common Issues and Solutions

### "Failed to connect to YouTube"

**Possible causes:**
1. Backend not running
2. JWT token expired
3. Network error
4. Backend error

**Solutions:**
1. Check backend is running: `./status.sh`
2. Logout and login again
3. Check backend logs for errors
4. Restart backend: `./stop.sh && ./start.sh`

### "redirect_uri_mismatch"

**Cause:** The redirect URI in Google Console doesn't match the one in your code.

**Solution:**
1. Check `.env` file: `YOUTUBE_REDIRECT_URI=http://localhost:8000/api/auth/platforms/youtube/callback`
2. Update Google Console to match exactly
3. No trailing slash!

### "invalid_state"

**Cause:** CSRF token mismatch or expired.

**Solution:**
1. Clear browser cookies
2. Logout and login again
3. Try in incognito mode

### Connection shows but doesn't work

**Cause:** Token might be expired or invalid.

**Solution:**
1. Disconnect the platform
2. Connect again
3. Check token expiration in database

### Backend logs show errors

Look for specific error messages:
- `AttributeError` - Code issue, check the implementation
- `KeyError` - Missing configuration
- `ConnectionError` - Database or network issue
- `ValidationError` - Invalid data format

## Still Having Issues?

1. Check all services are running:
   ```bash
   ./status.sh
   ```

2. Restart everything:
   ```bash
   ./stop.sh && ./start.sh
   ```

3. Check the full backend logs:
   ```bash
   cat logs/backend.log | grep -i "error\|exception" | tail -20
   ```

4. Enable debug mode in `.env`:
   ```
   DEBUG=true
   ```

5. Check the API docs:
   http://localhost:8000/docs
   
   Try the `/api/auth/platforms/youtube/authorize` endpoint directly from the docs.
