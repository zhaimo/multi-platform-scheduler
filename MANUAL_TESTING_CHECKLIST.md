# Manual Testing Checklist

## Test Environment Setup
- [ ] Backend running on http://localhost:8000
- [ ] Frontend running on http://localhost:3000
- [ ] PostgreSQL database accessible
- [ ] Redis server running
- [ ] Celery worker running
- [ ] AWS S3 bucket configured (or local storage)

## 1. User Authentication Flow

### Registration
- [ ] Navigate to /register
- [ ] Test with invalid email format → Should show validation error
- [ ] Test with weak password → Should show validation error
- [ ] Register with valid credentials → Should redirect to dashboard
- [ ] Try registering with same email → Should show "Email already registered" error
- [ ] Verify JWT tokens stored in localStorage

### Login
- [ ] Navigate to /login
- [ ] Test with incorrect credentials → Should show error message
- [ ] Test with correct credentials → Should redirect to dashboard
- [ ] Verify access token and refresh token stored
- [ ] Test "Remember me" functionality (if implemented)

### Token Refresh
- [ ] Wait for access token to expire (or manually delete it)
- [ ] Make an API request → Should auto-refresh token
- [ ] Verify new access token stored
- [ ] Test with invalid refresh token → Should redirect to login

### Logout
- [ ] Click logout button
- [ ] Verify tokens removed from localStorage
- [ ] Verify redirect to login page
- [ ] Try accessing protected route → Should redirect to login

## 2. Platform Connection Flow

### TikTok Connection
- [ ] Navigate to /dashboard/platforms
- [ ] Click "Connect" on TikTok card
- [ ] Verify redirect to TikTok OAuth page
- [ ] Authorize the app
- [ ] Verify redirect back to callback page
- [ ] Verify platform shows as "Connected"
- [ ] Verify platform username displayed
- [ ] Test disconnect functionality

### YouTube Connection
- [ ] Click "Connect" on YouTube card
- [ ] Complete OAuth flow
- [ ] Verify connection status updated
- [ ] Test with account that doesn't have YouTube channel → Should show error

### Instagram Connection
- [ ] Click "Connect" on Instagram card
- [ ] Complete OAuth flow
- [ ] Verify Business/Creator account requirement message
- [ ] Test with personal account → Should show appropriate error

### Facebook Connection
- [ ] Click "Connect" on Facebook card
- [ ] Complete OAuth flow
- [ ] Verify connection status updated
- [ ] Test page selection (if multiple pages)

## 3. Video Upload and Management

### Video Upload
- [ ] Navigate to /dashboard/videos
- [ ] Click "Upload Video" button
- [ ] Test drag-and-drop functionality
- [ ] Test file selection via button
- [ ] Upload invalid file type (e.g., .txt) → Should show error
- [ ] Upload file > 500MB → Should show size error
- [ ] Upload valid MP4 file → Should show progress bar
- [ ] Verify video appears in library after upload
- [ ] Verify thumbnail generated
- [ ] Add title, description, tags, category
- [ ] Verify metadata saved correctly

### Video Library
- [ ] Verify all uploaded videos displayed
- [ ] Test search functionality by title
- [ ] Test filter by tags
- [ ] Test filter by category
- [ ] Test filter by date range
- [ ] Click on video → Should open detail modal
- [ ] Verify video playback in modal
- [ ] Test edit video metadata
- [ ] Test delete video → Should show confirmation
- [ ] Confirm delete → Video should be removed

### Video Detail Modal
- [ ] Open video detail modal
- [ ] Verify video plays correctly
- [ ] Verify metadata displayed (title, description, tags, category)
- [ ] Verify file info (format, resolution, duration, size)
- [ ] Verify analytics section (if video posted)
- [ ] Test close modal functionality

## 4. Post Creation Flow

### Single Platform Post
- [ ] Navigate to /dashboard/posts/new
- [ ] Select a video from dropdown
- [ ] Verify video preview displayed
- [ ] Select one platform (e.g., TikTok)
- [ ] Enter caption (test character counter)
- [ ] Enter hashtags
- [ ] Test caption exceeding platform limit → Should show error
- [ ] Click "Post Now"
- [ ] Verify post created with "pending" status
- [ ] Wait for post to complete → Status should update to "posted"
- [ ] Verify platform URL displayed

### Multi-Platform Post
- [ ] Select multiple platforms
- [ ] Enter platform-specific captions
- [ ] Verify each platform has separate caption field
- [ ] Verify character counters for each platform
- [ ] Post to all selected platforms
- [ ] Verify separate post records created for each platform
- [ ] Verify all posts execute concurrently

### Template Usage
- [ ] Create a new template with platform-specific configs
- [ ] Select template from dropdown in post creation
- [ ] Verify fields auto-populated
- [ ] Modify template values
- [ ] Post with template
- [ ] Verify template not modified (only instance used)

### Post Validation
- [ ] Try posting without selecting video → Should show error
- [ ] Try posting without selecting platforms → Should show error
- [ ] Try posting to disconnected platform → Should show error
- [ ] Try posting with empty caption → Should show error (if required)
- [ ] Try posting video that doesn't meet platform requirements → Should show error

## 5. Scheduling Flow

### Schedule Future Post
- [ ] Navigate to post creation
- [ ] Select "Schedule for later"
- [ ] Select date/time in past → Should show validation error
- [ ] Select date/time < 5 minutes in future → Should show error
- [ ] Select valid future date/time
- [ ] Create scheduled post
- [ ] Navigate to /dashboard/schedules
- [ ] Verify schedule appears in upcoming list
- [ ] Wait for scheduled time → Post should execute automatically
- [ ] Verify post status updated

### Recurring Schedule
- [ ] Create recurring schedule (daily/weekly/monthly)
- [ ] Specify platforms and caption variations
- [ ] Verify schedule created
- [ ] Wait for first occurrence → Should create post
- [ ] Verify next occurrence calculated correctly
- [ ] Test caption rotation (if multiple captions provided)
- [ ] Test pause schedule functionality
- [ ] Test resume schedule functionality
- [ ] Test cancel schedule → Should stop future occurrences

### Schedule Management
- [ ] View all schedules in /dashboard/schedules
- [ ] Filter by active/paused/completed
- [ ] Edit schedule (change time, platforms, captions)
- [ ] Verify changes saved
- [ ] Delete schedule → Should show confirmation
- [ ] Confirm delete → Schedule removed

## 6. Reposting Flow

### Basic Repost
- [ ] Navigate to video library
- [ ] Click "Repost" on a previously posted video
- [ ] Verify repost modal opens
- [ ] Verify original post metadata pre-filled
- [ ] Modify caption and hashtags
- [ ] Select platforms for repost
- [ ] Verify last post date displayed for each platform
- [ ] Try reposting to same platform within 24 hours → Should show error
- [ ] Repost to allowed platforms
- [ ] Verify new post records created

### Repost with Schedule
- [ ] Open repost modal
- [ ] Select "Schedule for later"
- [ ] Set future date/time
- [ ] Create scheduled repost
- [ ] Verify appears in schedules list
- [ ] Wait for execution → Should post at scheduled time

### Recurring Repost
- [ ] Create recurring repost schedule
- [ ] Provide multiple caption variations
- [ ] Verify captions rotate on each occurrence
- [ ] Test 24-hour restriction between reposts
- [ ] Verify recurring pattern respected

## 7. Post Dashboard

### Post List View
- [ ] Navigate to /dashboard/posts
- [ ] Verify all posts displayed
- [ ] Verify status indicators (pending, posted, failed)
- [ ] Verify platform icons displayed
- [ ] Test filter by platform
- [ ] Test filter by status
- [ ] Test filter by date range
- [ ] Test search by video title

### Post Details
- [ ] Click on a post
- [ ] Verify post details displayed
- [ ] For posted videos, verify platform URL clickable
- [ ] For failed posts, verify error message displayed
- [ ] Test retry failed post functionality
- [ ] Test delete post functionality

### Real-time Updates
- [ ] Create a new post
- [ ] Keep dashboard open
- [ ] Verify status updates automatically (polling or WebSocket)
- [ ] Verify no page refresh needed
- [ ] Test with multiple posts updating simultaneously

## 8. Template Management

### Create Template
- [ ] Navigate to templates section
- [ ] Click "Create Template"
- [ ] Enter template name
- [ ] Configure platform-specific captions and hashtags
- [ ] Save template
- [ ] Verify template appears in list

### Use Template
- [ ] Go to post creation
- [ ] Select template from dropdown
- [ ] Verify fields populated correctly
- [ ] Modify values (should not affect template)
- [ ] Create post successfully

### Edit Template
- [ ] Open template list
- [ ] Click edit on a template
- [ ] Modify values
- [ ] Save changes
- [ ] Verify changes reflected in template list
- [ ] Use template in new post → Should use updated values

### Delete Template
- [ ] Click delete on a template
- [ ] Verify confirmation dialog
- [ ] Confirm delete
- [ ] Verify template removed from list

## 9. Analytics and Monitoring

### Video Analytics
- [ ] Open video detail modal for posted video
- [ ] Verify analytics section displayed
- [ ] Verify metrics for each platform (views, likes, comments, shares)
- [ ] Verify last sync timestamp
- [ ] Test manual refresh analytics
- [ ] Wait for automatic sync (6 hours) → Should update

### Dashboard Analytics
- [ ] View overall statistics on dashboard
- [ ] Verify total videos count
- [ ] Verify total posts count
- [ ] Verify success rate
- [ ] Test date range filter for analytics

## 10. Notifications

### Email Notifications
- [ ] Configure email in notification preferences
- [ ] Create a post
- [ ] Wait for completion → Should receive email
- [ ] Create a post that will fail → Should receive failure email
- [ ] Test notification batching (multiple posts within 5 minutes)

### In-App Notifications
- [ ] Verify notification bell icon in header
- [ ] Create posts → Should see notification count
- [ ] Click notification bell → Should show list
- [ ] Click notification → Should navigate to relevant page
- [ ] Mark notification as read
- [ ] Test clear all notifications

### Notification Preferences
- [ ] Navigate to user settings
- [ ] Toggle notification preferences
- [ ] Disable post success notifications
- [ ] Create successful post → Should not receive notification
- [ ] Enable failure notifications only
- [ ] Create failed post → Should receive notification

## 11. Error Handling

### Network Errors
- [ ] Disconnect internet
- [ ] Try any API operation → Should show connection error
- [ ] Reconnect internet
- [ ] Retry operation → Should work

### Platform API Errors
- [ ] Revoke platform access externally
- [ ] Try posting → Should show auth error
- [ ] Should prompt to reconnect platform

### Rate Limiting
- [ ] Make > 100 requests in 1 minute
- [ ] Verify 429 status returned
- [ ] Verify retry-after header respected
- [ ] Wait for rate limit reset → Should work again

### Validation Errors
- [ ] Test all form validations
- [ ] Verify clear error messages displayed
- [ ] Verify error messages positioned near relevant fields
- [ ] Test multiple validation errors simultaneously

### Server Errors
- [ ] Simulate 500 error (stop backend temporarily)
- [ ] Try operation → Should show generic error message
- [ ] Verify error logged to monitoring system
- [ ] Restart backend → Should recover

## 12. Mobile Responsiveness

### Mobile Layout (< 640px)
- [ ] Test on iPhone SE (375px width)
- [ ] Verify navigation menu collapses to hamburger
- [ ] Verify all pages readable without horizontal scroll
- [ ] Test login/register forms
- [ ] Test video upload on mobile
- [ ] Test post creation form
- [ ] Verify modals fit on screen
- [ ] Test touch interactions (tap, swipe)

### Tablet Layout (640px - 1024px)
- [ ] Test on iPad (768px width)
- [ ] Verify grid layouts adjust appropriately
- [ ] Test video library grid (should show 2-3 columns)
- [ ] Test post creation layout
- [ ] Verify navigation remains accessible

### Desktop Layout (> 1024px)
- [ ] Test on standard desktop (1920px width)
- [ ] Verify full navigation visible
- [ ] Verify optimal grid layouts (4 columns for videos)
- [ ] Test side-by-side layouts in post creation
- [ ] Verify modals centered and sized appropriately

### Cross-Browser Testing
- [ ] Test on Chrome (latest)
- [ ] Test on Firefox (latest)
- [ ] Test on Safari (latest)
- [ ] Test on Edge (latest)
- [ ] Verify consistent behavior across browsers

## 13. Performance Testing

### Upload Performance
- [ ] Upload small video (< 10MB) → Should complete quickly
- [ ] Upload medium video (50-100MB) → Should show progress
- [ ] Upload large video (400-500MB) → Should handle without timeout
- [ ] Test concurrent uploads (2-3 videos) → Should handle gracefully

### Page Load Performance
- [ ] Measure initial page load time
- [ ] Test with 100+ videos in library → Should paginate or lazy load
- [ ] Test with 100+ posts → Should perform well
- [ ] Verify images lazy load
- [ ] Check for memory leaks (keep app open for extended period)

### API Response Times
- [ ] Monitor API response times
- [ ] Verify most endpoints respond < 500ms
- [ ] Verify video upload endpoint handles large files
- [ ] Test with slow network (throttle to 3G) → Should still be usable

## 14. Security Testing

### Authentication Security
- [ ] Verify JWT tokens expire correctly
- [ ] Test with expired token → Should refresh automatically
- [ ] Test with invalid token → Should redirect to login
- [ ] Verify tokens not exposed in URLs
- [ ] Verify tokens stored securely (httpOnly cookies preferred)

### Authorization
- [ ] Try accessing another user's video → Should return 403
- [ ] Try modifying another user's post → Should return 403
- [ ] Try deleting another user's schedule → Should return 403
- [ ] Verify all endpoints check user ownership

### Input Validation
- [ ] Test SQL injection in search fields
- [ ] Test XSS in caption fields
- [ ] Test file upload with malicious files
- [ ] Verify all inputs sanitized
- [ ] Test CSRF protection (if applicable)

### Platform Token Security
- [ ] Verify platform tokens encrypted in database
- [ ] Verify tokens not exposed in API responses
- [ ] Verify tokens not logged
- [ ] Test token refresh before expiration

## 15. Data Integrity

### Video Data
- [ ] Upload video → Verify file stored correctly
- [ ] Delete video → Verify file removed from storage
- [ ] Verify thumbnail generated and stored
- [ ] Test with corrupted video file → Should handle gracefully

### Post Data
- [ ] Create post → Verify all fields saved correctly
- [ ] Update post status → Verify changes persisted
- [ ] Delete post → Verify cascade deletes (if applicable)
- [ ] Verify post history maintained

### User Data
- [ ] Update user profile → Verify changes saved
- [ ] Delete user account → Verify cascade deletes
- [ ] Verify user data isolated (no cross-user data leaks)

## Test Results Summary

### Critical Issues Found
- [ ] Issue 1: [Description]
- [ ] Issue 2: [Description]

### Medium Priority Issues
- [ ] Issue 1: [Description]
- [ ] Issue 2: [Description]

### Low Priority Issues / Enhancements
- [ ] Issue 1: [Description]
- [ ] Issue 2: [Description]

### Test Coverage
- Authentication: ____%
- Platform Connections: ____%
- Video Management: ____%
- Post Creation: ____%
- Scheduling: ____%
- Reposting: ____%
- Mobile Responsiveness: ____%
- Error Handling: ____%

### Overall Status
- [ ] Ready for production
- [ ] Needs minor fixes
- [ ] Needs major fixes
- [ ] Not ready for production

### Notes
[Add any additional observations or recommendations]
