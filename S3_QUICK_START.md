# AWS S3 Quick Start

## TL;DR - Get S3 Working in 5 Minutes

### 1. Create S3 Bucket (AWS Console)
1. Go to https://s3.console.aws.amazon.com
2. Click "Create bucket"
3. Name it (e.g., `my-video-app-2024`)
4. Choose region (e.g., `us-east-1`)
5. Keep "Block all public access" CHECKED
6. Click "Create bucket"

### 2. Configure CORS
1. Click on your bucket
2. Go to "Permissions" tab
3. Scroll to "CORS" → Click "Edit"
4. Paste this:
```json
[{
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
    "AllowedOrigins": ["http://localhost:3000"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3000
}]
```
5. Save

### 3. Create IAM User
1. Go to https://console.aws.amazon.com/iam/
2. Click "Users" → "Create user"
3. Name: `video-app-user`
4. Click "Next"
5. Select "Attach policies directly"
6. Search and select "AmazonS3FullAccess"
7. Click "Create user"

### 4. Get Access Keys
1. Click on the user you just created
2. Go to "Security credentials" tab
3. Click "Create access key"
4. Select "Application running outside AWS"
5. Click "Create access key"
6. **COPY BOTH KEYS** (you won't see the secret again!)

### 5. Configure Your App

**Option A: Use the setup script (Easiest)**
```bash
cd multi-platform-scheduler
./setup-s3.sh
```

**Option B: Manual configuration**
Edit `backend/.env`:
```bash
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1
S3_BUCKET_NAME=my-video-app-2024
```

### 6. Restart Backend
```bash
cd backend
pkill -f "uvicorn main:app"
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
```

### 7. Test It!
1. Go to http://localhost:3000/dashboard/videos
2. Click "Upload Video"
3. Select a video file
4. Upload! 🎉

## Troubleshooting

**"Access Denied"**
- Check IAM user has S3 permissions
- Verify credentials in `.env` are correct

**"Bucket not found"**
- Check bucket name matches exactly
- Verify region is correct

**"CORS error"**
- Make sure CORS is configured on the bucket
- Check AllowedOrigins includes `http://localhost:3000`

## Need More Help?

See the full guide: `AWS_S3_SETUP.md`
