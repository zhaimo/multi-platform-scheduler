# Quick Test Guide

## 🚀 Fast Track Testing

This guide helps you quickly test the most critical features of the Multi-Platform Video Scheduler.

---

## Prerequisites

Before testing, ensure you have:
- ✅ Backend running on `http://localhost:8000`
- ✅ Frontend running on `http://localhost:3000`
- ✅ PostgreSQL database accessible
- ✅ Redis server running
- ✅ At least one platform OAuth configured (TikTok recommended)

---

## 5-Minute Smoke Test

### 1. Authentication (2 minutes)
```
1. Go to http://localhost:3000/register
2. Register with: test@example.com / Password123!
3. Should redirect to dashboard
4. Logout
5. Login with same credentials
6. Should redirect to dashboard
```

### 2. Platform Connection (1 minute)
```
1. Go to /dashboard/platforms
2. Click "Connect" on TikTok
3. Complete OAuth flow
4. Verify "Connected" status shows
```

### 3. Video Upload (2 minutes)
```
1. Go to /dashboard/videos
2. Click "Upload Video"
3. Drag and drop a video file (MP4, < 500MB)
4. Fill in title
5. Click "Upload"
6. Verify video appears in library
```

**✅ If all 3 tests pass, core functionality is working!**

---

## 15-Minute Core Feature Test

### 1. Complete Auth Flow (3 minutes)
- Register new user
- Login
- Check token in localStorage
- Wait 15 minutes for token expiration
- Make API call (should auto-refresh)
- Logout

### 2. Video Management (4 minutes)
- Upload video
- Edit video metadata (title, tags, category)
- Search for video
- Filter by tag
- Delete video

### 3. Post Creation (4 minutes)
- Select video
- Choose platform (TikTok)
- Enter caption and hashtags
- Post immediately
- Verify post status updates to "posted"
- Check platform URL

### 4. Repost with Restriction (4 minutes)
- Try to repost same video immediately
- Should show "24-hour restriction" error
- Verify error message shows hours remaining

---

## 30-Minute Full Feature Test

Follow the 15-minute test, then add:

### 5. Scheduling (5 minutes)
- Create scheduled post for 10 minutes in future
- Verify appears in schedules list
- Wait for scheduled time
- Verify post executes automatically

### 6. Multi-Platform Posting (5 minutes)
- Connect multiple platforms
- Create post for all platforms
- Verify separate post records created
- Check all posts execute

### 7. Templates (3 minutes)
- Create template with platform-specific captions
- Use template in new post
- Verify fields auto-populate

### 8. Mobile Testing (2 minutes)
- Open on mobile device or resize browser to 375px
- Test navigation
- Test video upload
- Test post creation

---

## Critical Bug Checks

### Must Verify These Work:

1. **SSR Safety** ✅
   - Refresh page while logged in
   - Should not crash
   - Should maintain auth state

2. **24-Hour Restriction** ✅
   - Post video to platform
   - Try reposting immediately
   - Should block with clear error message

3. **Token Refresh** ✅
   - Wait for token expiration
   - Make API call
   - Should auto-refresh without redirect

4. **File Validation** ✅
   - Try uploading non-video file
   - Should show error
   - Try uploading > 500MB file
   - Should show error

---

## Common Issues & Solutions

### Issue: "Cannot connect to backend"
**Solution**: Check backend is running on port 8000
```bash
cd backend
uvicorn main:app --reload
```

### Issue: "Database connection failed"
**Solution**: Check PostgreSQL is running
```bash
docker-compose up -d postgres
```

### Issue: "OAuth redirect fails"
**Solution**: Check redirect URI matches in platform app settings

### Issue: "Video upload fails"
**Solution**: Check S3 credentials in .env file

### Issue: "Scheduled posts don't execute"
**Solution**: Check Celery worker and Redis are running
```bash
docker-compose up -d redis
celery -A src.celery_app worker --loglevel=info
celery -A src.celery_app beat --loglevel=info
```

---

## Test Data Recommendations

### Test Videos
- Small: 5-10MB MP4 (for quick tests)
- Medium: 50-100MB MP4 (for realistic tests)
- Large: 400-500MB MP4 (for stress tests)

### Test Captions
- Short: "Test post #testing"
- Medium: 500 characters with hashtags
- Long: 2000+ characters (test platform limits)

### Test Schedules
- Immediate: Post now
- Near future: 10 minutes from now
- Far future: 1 day from now
- Recurring: Daily at specific time

---

## Performance Benchmarks

### Expected Response Times
- Login: < 500ms
- Video upload (10MB): < 5 seconds
- Post creation: < 1 second
- Schedule creation: < 500ms
- Video list (100 videos): < 1 second

### If Slower Than Expected
1. Check database indexes
2. Check network latency
3. Check S3 upload speed
4. Check Celery worker status

---

## Mobile Testing Checklist

### Breakpoints to Test
- 📱 375px (iPhone SE)
- 📱 768px (iPad)
- 💻 1024px (Desktop)
- 💻 1920px (Large Desktop)

### Features to Verify
- ✅ Navigation collapses on mobile
- ✅ Forms are usable
- ✅ Modals fit screen
- ✅ Touch interactions work
- ✅ No horizontal scroll

---

## Security Quick Checks

### Must Verify:
1. ✅ Cannot access other users' videos
2. ✅ Cannot modify other users' posts
3. ✅ Tokens expire correctly
4. ✅ Invalid tokens redirect to login
5. ✅ File uploads are validated
6. ✅ SQL injection attempts fail
7. ✅ XSS attempts are sanitized

---

## When to Stop Testing

### ✅ Green Light (Ready for Production)
- All smoke tests pass
- All core features work
- No critical bugs found
- Mobile responsive
- Security checks pass

### ⚠️ Yellow Light (Needs Minor Fixes)
- Core features work
- Some edge cases fail
- Minor UI issues
- Performance acceptable

### 🛑 Red Light (Not Ready)
- Core features broken
- Critical bugs present
- Security issues found
- Performance unacceptable

---

## Quick Commands

### Start Everything
```bash
# Backend
cd backend
uvicorn main:app --reload

# Frontend
cd frontend
npm run dev

# Workers
celery -A src.celery_app worker --loglevel=info
celery -A src.celery_app beat --loglevel=info
```

### Run Tests
```bash
# Backend validation
cd backend
python3 test_basic.py

# Frontend build check
cd frontend
npm run build
```

### Check Logs
```bash
# Backend logs
tail -f backend/logs/app.log

# Celery logs
tail -f backend/logs/celery.log

# Frontend logs
# Check browser console
```

---

## Need More Detail?

- **Full Test Cases**: See `MANUAL_TESTING_CHECKLIST.md`
- **Bug Fixes**: See `BUG_FIXES.md`
- **Test Summary**: See `TESTING_SUMMARY.md`
- **Complete Report**: See `TESTING_COMPLETE.md`

---

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review error logs
3. Check environment variables
4. Verify all services are running
5. Consult the full documentation

**Happy Testing! 🎉**
