# TikTok Developer Application - Detailed Form Guide

## Step-by-Step Form Filling Guide

### Page 1: Developer Registration

#### 1. Account Type
**Field**: "Select account type"
**Choose**: `Individual` (unless you have a registered company)
**Why**: Simpler approval process, no business documents needed

#### 2. First Name
**Field**: "First Name"
**Enter**: Your legal first name
**Example**: `John`

#### 3. Last Name
**Field**: "Last Name"
**Enter**: Your legal last name
**Example**: `Smith`

#### 4. Email Address
**Field**: "Email"
**Enter**: Your active email address (you'll receive approval here)
**Example**: `[email]`
**Tip**: Use a professional email, not a temporary one

#### 5. Country/Region
**Field**: "Country/Region"
**Select**: Your current country
**Example**: `United States`

#### 6. Phone Number (Optional)
**Field**: "Phone Number"
**Enter**: Your phone number with country code
**Example**: `+1 555-123-4567`
**Tip**: Optional but may speed up approval

---

### Page 2: Application Details

#### 7. Application Name
**Field**: "What will you name your application?"
**Enter**: 
```
Multi-Platform Video Scheduler
```
**Why**: Clear, professional name that describes the purpose

#### 8. Application Category
**Field**: "Select a category"
**Choose**: `Productivity` or `Social Media Management`
**Why**: Best fits a scheduling tool

#### 9. Application Description
**Field**: "Describe your application" (Usually 100-500 characters)
**Enter**:
```
A productivity tool that helps content creators schedule and publish videos across multiple social media platforms including TikTok, YouTube, and Twitter. Users can upload videos once and schedule them to post automatically at optimal times, manage captions, and track posting history from a unified dashboard.
```

**Alternative shorter version** (if character limit):
```
Video scheduling tool for content creators to post across TikTok, YouTube, and Twitter from one dashboard. Features include automated posting, caption management, and scheduling.
```

#### 10. Use Case / Purpose
**Field**: "What will you use the TikTok API for?" or "Describe your use case"
**Enter**:
```
I am building a multi-platform video scheduling application that will use the TikTok Content Posting API to:

1. Allow users to authenticate with their TikTok accounts via OAuth 2.0
2. Upload and publish videos to TikTok on behalf of authenticated users
3. Schedule videos to be posted at specific times
4. Retrieve basic user information to display in the dashboard

The application will help content creators save time by managing their social media presence across multiple platforms from a single interface. All video uploads will comply with TikTok's community guidelines and terms of service.
```

#### 11. Website URL (Optional)
**Field**: "Website" or "Application URL"
**Options**:
- If you have a GitHub repo: `https://github.com/yourusername/video-scheduler`
- If deploying: `https://yourdomain.com`
- If neither: Leave blank or put `http://localhost:3000` (development)

**Example**: `https://github.com/yourusername/multi-platform-scheduler`

#### 12. Expected Monthly Active Users
**Field**: "How many users do you expect?"
**Choose**: `0-1,000` or `1,000-10,000`
**Why**: Be realistic for a new app

#### 13. Expected API Calls Per Day
**Field**: "Expected API usage"
**Choose**: `0-1,000` or `1,000-10,000`
**Why**: Start conservative, can increase later

---

### Page 3: API Permissions (After Initial Approval)

#### 14. Required Scopes
**Field**: "Select the permissions you need"
**Check these boxes**:
- ☑ `user.info.basic` - Get user profile information
- ☑ `video.upload` - Upload videos
- ☑ `video.publish` - Publish videos to TikTok

#### 15. Justification for Each Scope
**For `user.info.basic`**:
```
Required to display the authenticated user's TikTok username and profile picture in the application dashboard, allowing users to confirm they're posting to the correct account.
```

**For `video.upload`**:
```
Core functionality - allows users to upload their video files to TikTok through our scheduling interface. Videos are uploaded directly from the user's device to TikTok's servers.
```

**For `video.publish`**:
```
Essential for the scheduling feature - enables the application to publish uploaded videos to the user's TikTok account at their specified scheduled time.
```

---

## Important Tips

### Do's ✅
- Be honest and specific about your use case
- Use professional language
- Mention you'll comply with TikTok's policies
- Provide a real email you check regularly
- Be patient - approval takes 1-3 business days

### Don'ts ❌
- Don't mention automation or bots
- Don't say you'll post on behalf of others without permission
- Don't mention scraping or data collection
- Don't use temporary/fake email addresses
- Don't rush - read each question carefully

---

## After Submission

### What Happens Next?

1. **Immediate**: You'll see a "Pending Review" status
2. **Within 24 hours**: Confirmation email that application was received
3. **1-3 business days**: Approval or rejection email
4. **If approved**: You can create apps and request API access
5. **If rejected**: Email will explain why - you can reapply

### Check Your Email
- Check spam/junk folder
- Look for emails from `noreply@tiktok.com` or `developers@tiktok.com`
- Add these to your contacts to avoid missing updates

### While Waiting
- Continue developing with YouTube and Twitter (already working!)
- Prepare your video content
- Test other features of your app
- Read TikTok's API documentation

---

## Common Rejection Reasons & How to Avoid

### ❌ Vague Use Case
**Bad**: "I want to use TikTok API"
**Good**: "Building a scheduling tool for content creators to post videos"

### ❌ Suspicious Intent
**Bad**: "Automate posting for multiple accounts"
**Good**: "Help individual users schedule their own content"

### ❌ Incomplete Information
**Bad**: Leaving fields blank
**Good**: Fill out all required fields thoroughly

### ❌ Unprofessional Email
**Bad**: `cooldude123@tempmail.com`
**Good**: `[email]` or `[email]`

---

## Quick Reference - Copy/Paste Ready

### Application Name
```
Multi-Platform Video Scheduler
```

### Short Description
```
Video scheduling tool for content creators to manage posts across TikTok, YouTube, and Twitter.
```

### Full Use Case
```
Building a multi-platform video scheduling application using TikTok Content Posting API to allow users to authenticate, upload, and schedule videos to their TikTok accounts. The app helps content creators manage their social media presence efficiently while complying with all TikTok policies.
```

### Scope Justifications
**user.info.basic**:
```
Display authenticated user's profile in dashboard for account verification.
```

**video.upload**:
```
Core functionality to upload user videos to TikTok through our interface.
```

**video.publish**:
```
Enable scheduled publishing of videos at user-specified times.
```

---

## Need Help?

If your application is rejected:
1. Read the rejection email carefully
2. Address the specific concerns mentioned
3. Wait 7 days before reapplying
4. Revise your use case description
5. Try again with more detail

If you have questions:
- TikTok Developer Forum: https://developers.tiktok.com/community
- Documentation: https://developers.tiktok.com/doc

---

## Timeline Expectations

- **Form completion**: 10-15 minutes
- **Initial review**: 1-3 business days
- **Scope approval**: Additional 1-3 days after app creation
- **Total time**: 2-6 business days typically

Good luck with your application! 🎉
