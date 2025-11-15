# Manual Testing Guide

This guide walks you through testing all core features of the Multi-Platform Video Scheduler.

## Prerequisites

Before testing, ensure:
- ✅ Backend is running on http://localhost:8000
- ✅ Frontend is running on http://localhost:3000
- ✅ PostgreSQL and Redis are running
- ✅ You have valid API credentials for at least one platform (TikTok, YouTube, Instagram, or Facebook)
- ✅ You have a test video file ready (MP4, MOV, AVI, or WebM, under 500MB)

Check services status:
```bash
cd multi-platform-scheduler
./status.sh
```

## Test Flow 1: User Registration & Login

### 1.1 Register a New Account
1. Navigate to http://localhost:3000
2. Click "Register" or "Sign Up"
3. Enter email and password
4. Click "Register"
5. **Expected**: Successfully redirected to dashboard

### 1.2 Login
1. Log out if logged in
2. Navigate to http://localhost:3000
3. Enter your credentials
4. Click "Login"
5. **Expected**: Successfully redirected to dashboard

**✅ Pass / ❌ Fail**: _______

---

## Test Flow 2: Video Upload

### 2.1 Upload a Video
1. Go to "Videos" page in dashboard
2. Click "Upload Video" button
3. Select or drag-and-drop a video file
4. Fill in:
   - Title: "Test Video 1"
   - Description: "This is a test video"
   - Tags: "test, demo"
   - Category: "entertainment"
5. Click "Upload"
6. **Expected**: 
   - Upload progress bar appears
   - Video appears in library after upload
   - Thumbnail is visible

### 2.2 View Video Details
1. Click on the uploaded video thumbnail
2. **Expected**:
   - Modal opens showing video details
   - Video player works
   - Thumbnail displays correctly
   - Metadata is correct (duration, resolution, size)
   - Analytics section shows "No analytics available yet"

**✅ Pass / ❌ Fail**: _______

---

## Test Flow 3: Platform Connection

### 3.1 Navigate to Platforms Page
1. Go to "Platforms" page in dashboard
2. **Expected**: See list of available platforms (TikTok, YouTube, Instagram, Facebook)

### 3.2 Connect a Platform (Choose One)

#### Option A: TikTok
1. Click "Connect" on TikTok card
2. **Expected**: Redirected to TikTok OAuth page
3. Log in to TikTok and authorize the app
4. **Expected**: Redirected back to app, TikTok shows as "Connected"

#### Option B: YouTube
1. Click "Connect" on YouTube card
2. **Expected**: Redirected to Google OAuth page
3. Log in to Google and authorize the app
4. **Expected**: Redirected back to app, YouTube shows as "Connected"

#### Option C: Instagram
1. Click "Connect" on Instagram card
2. **Expected**: Redirected to Facebook/Instagram OAuth page
3. Log in and authorize the app
4. **Expected**: Redirected back to app, Instagram shows as "Connected"

#### Option D: Facebook
1. Click "Connect" on Facebook card
2. **Expected**: Redirected to Facebook OAuth page
3. Log in and authorize the app
4. **Expected**: Redirected back to app, Facebook shows as "Connected"

**✅ Pass / ❌ Fail**: _______

**Notes**: If OAuth fails, check:
- Platform API credentials in `.env` file
- Redirect URLs are correctly configured in platform developer console
- Backend logs for specific errors: `tail -f logs/backend.log`

---

## Test Flow 4: Create a Post (Immediate)

### 4.1 Navigate to Create Post
1. Go to "Posts" → "New Post" in dashboard
2. **Expected**: Post creation form appears

### 4.2 Fill Out Post Form
1. Select your uploaded video from dropdown
2. Select the platform(s) you connected
3. For each platform, enter:
   - Caption/Description
   - Hashtags (if applicable)
4. Leave "Schedule for later" unchecked
5. Click "Create Post"

### 4.3 Verify Post Creation
1. **Expected**: Success message appears
2. Go to "Posts" page
3. **Expected**: 
   - New post appears in list
   - Status shows "pending" or "processing"
   - After a few moments, status updates to "completed" or "failed"

### 4.4 Check Platform
1. Go to the actual platform (TikTok/YouTube/Instagram/Facebook)
2. **Expected**: Video appears on your profile/channel

**✅ Pass / ❌ Fail**: _______

**Notes**: If posting fails:
- Check backend logs: `tail -f logs/backend.log`
- Check Celery worker logs: `tail -f logs/celery.log`
- Verify platform API credentials and permissions

---

## Test Flow 5: Schedule a Post

### 5.1 Create Scheduled Post
1. Go to "Posts" → "New Post"
2. Select a video and platform(s)
3. Enter caption/description
4. Check "Schedule for later"
5. Select a date/time at least 5 minutes in the future
6. Click "Create Post"

### 5.2 Verify Schedule
1. Go to "Schedules" page
2. **Expected**: 
   - Scheduled post appears in list
   - Shows correct date/time
   - Status is "pending"

### 5.3 Wait for Scheduled Time
1. Wait until the scheduled time passes
2. Refresh the "Posts" page
3. **Expected**: 
   - Post appears in posts list
   - Status changes from "pending" to "completed"

**✅ Pass / ❌ Fail**: _______

---

## Test Flow 6: Repost a Video

### 6.1 Navigate to Videos
1. Go to "Videos" page
2. Find a video that was already posted

### 6.2 Initiate Repost
1. Click on the video thumbnail to open details
2. Click "Repost" button (or find repost option)
3. **Expected**: Repost modal opens

### 6.3 Configure Repost
1. Select platform(s) to repost to
2. Modify caption if desired
3. Click "Repost"

### 6.4 Verify Repost
1. **Expected**: Success message
2. Go to "Posts" page
3. **Expected**: New post appears with updated caption

### 6.5 Test 24-Hour Restriction
1. Try to repost the same video to the same platform immediately
2. **Expected**: Error message about 24-hour restriction

**✅ Pass / ❌ Fail**: _______

---

## Test Flow 7: Post Templates (Optional)

### 7.1 Create a Template
1. Go to "Templates" page (if available)
2. Click "Create Template"
3. Enter:
   - Template name: "Standard Post"
   - Default caption template
   - Default hashtags
4. Save template

### 7.2 Use Template
1. Go to "Posts" → "New Post"
2. Select the template from dropdown
3. **Expected**: Form auto-fills with template values

**✅ Pass / ❌ Fail**: _______

---

## Test Flow 8: Analytics

### 8.1 View Video Analytics
1. Wait at least 6 hours after posting (or manually trigger analytics sync)
2. Go to "Videos" page
3. Click on a posted video
4. **Expected**: Analytics section shows metrics (views, likes, comments, shares)

### 8.2 Manual Analytics Sync (Optional)
If you want to test immediately:
```bash
# Trigger analytics sync manually
cd multi-platform-scheduler/backend
source venv/bin/activate
python -c "from src.tasks import sync_analytics; sync_analytics.delay()"
```

**✅ Pass / ❌ Fail**: _______

---

## Test Flow 9: Error Handling

### 9.1 Test Invalid Video Upload
1. Try to upload a file that's not a video (e.g., .txt file)
2. **Expected**: Error message about invalid file type

### 9.2 Test File Size Limit
1. Try to upload a video larger than 500MB
2. **Expected**: Error message about file size

### 9.3 Test Post Without Platform Connection
1. Disconnect all platforms
2. Try to create a post
3. **Expected**: Error message about no connected platforms

**✅ Pass / ❌ Fail**: _______

---

## Test Flow 10: Notifications (Optional)

### 10.1 Check Notification Preferences
1. Go to user settings/profile
2. Find notification preferences
3. Enable email notifications for post completion

### 10.2 Verify Notifications
1. Create and post a video
2. **Expected**: Receive email notification when post completes

**✅ Pass / ❌ Fail**: _______

---

## Summary

| Test Flow | Status | Notes |
|-----------|--------|-------|
| 1. Registration & Login | ⬜ | |
| 2. Video Upload | ⬜ | |
| 3. Platform Connection | ⬜ | |
| 4. Create Post (Immediate) | ⬜ | |
| 5. Schedule Post | ⬜ | |
| 6. Repost Video | ⬜ | |
| 7. Post Templates | ⬜ | |
| 8. Analytics | ⬜ | |
| 9. Error Handling | ⬜ | |
| 10. Notifications | ⬜ | |

---

## Troubleshooting

### Backend Not Responding
```bash
cd multi-platform-scheduler
./status.sh
# If services are down:
./start.sh
```

### Check Logs
```bash
# Backend logs
tail -f logs/backend.log

# Frontend logs
tail -f logs/frontend.log

# Celery worker logs
tail -f logs/celery.log
```

### Database Issues
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Reset database (WARNING: deletes all data)
cd backend
source venv/bin/activate
alembic downgrade base
alembic upgrade head
```

### Platform API Issues
- Verify API credentials in `.env` file
- Check platform developer console for API status
- Ensure redirect URLs match exactly
- Check rate limits on platform APIs

---

## Next Steps After Testing

Once you've completed testing:
1. Document any bugs or issues found
2. Note which features work well
3. Identify areas for improvement
4. Consider deploying to production if all tests pass
