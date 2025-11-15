# AWS S3 Setup Guide for Video Storage

This guide will walk you through setting up AWS S3 for storing videos in the Multi-Platform Video Scheduler.

## Prerequisites

- AWS Account (create one at https://aws.amazon.com if you don't have one)
- AWS CLI installed (optional but recommended)

## Step 1: Create an S3 Bucket

### Option A: Using AWS Console (Recommended for beginners)

1. **Log in to AWS Console**
   - Go to https://console.aws.amazon.com
   - Sign in with your AWS account

2. **Navigate to S3**
   - Search for "S3" in the AWS services search bar
   - Click on "S3" to open the S3 console

3. **Create a New Bucket**
   - Click "Create bucket"
   - **Bucket name**: Choose a unique name (e.g., `my-video-scheduler-videos`)
     - Must be globally unique across all AWS accounts
     - Use lowercase letters, numbers, and hyphens only
   - **AWS Region**: Choose a region close to you (e.g., `us-east-1`)
   - **Block Public Access settings**: Keep all boxes CHECKED (we'll use pre-signed URLs)
   - **Bucket Versioning**: Disabled (optional)
   - **Tags**: Add if needed (optional)
   - **Default encryption**: Enable with SSE-S3 (recommended)
   - Click "Create bucket"

### Option B: Using AWS CLI

```bash
# Set your bucket name and region
BUCKET_NAME="my-video-scheduler-videos"
REGION="us-east-1"

# Create the bucket
aws s3 mb s3://$BUCKET_NAME --region $REGION

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket $BUCKET_NAME \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

## Step 2: Configure CORS for the Bucket

CORS (Cross-Origin Resource Sharing) allows your frontend to upload files directly to S3.

### Using AWS Console

1. Go to your bucket in S3 console
2. Click on the "Permissions" tab
3. Scroll down to "Cross-origin resource sharing (CORS)"
4. Click "Edit" and paste this configuration:

```json
[
    {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
        "AllowedOrigins": ["http://localhost:3000", "http://localhost:8000"],
        "ExposeHeaders": ["ETag"],
        "MaxAgeSeconds": 3000
    }
]
```

5. Click "Save changes"

**Note**: Update `AllowedOrigins` with your production domain when deploying.

### Using AWS CLI

```bash
cat > cors.json << 'EOF'
{
  "CORSRules": [
    {
      "AllowedHeaders": ["*"],
      "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
      "AllowedOrigins": ["http://localhost:3000", "http://localhost:8000"],
      "ExposeHeaders": ["ETag"],
      "MaxAgeSeconds": 3000
    }
  ]
}
EOF

aws s3api put-bucket-cors --bucket $BUCKET_NAME --cors-configuration file://cors.json
rm cors.json
```

## Step 3: Create IAM User with S3 Access

### Using AWS Console

1. **Navigate to IAM**
   - Search for "IAM" in AWS services
   - Click on "IAM"

2. **Create a New User**
   - Click "Users" in the left sidebar
   - Click "Create user"
   - **User name**: `video-scheduler-s3-user`
   - Click "Next"

3. **Set Permissions**
   - Select "Attach policies directly"
   - Search for and select "AmazonS3FullAccess" (or create a custom policy - see below)
   - Click "Next"
   - Click "Create user"

4. **Create Access Keys**
   - Click on the newly created user
   - Go to "Security credentials" tab
   - Scroll to "Access keys"
   - Click "Create access key"
   - Select "Application running outside AWS"
   - Click "Next"
   - Add description (optional): "Video Scheduler App"
   - Click "Create access key"
   - **IMPORTANT**: Copy both the "Access key ID" and "Secret access key"
   - Store them securely - you won't be able to see the secret again!

### Custom IAM Policy (More Secure - Recommended)

Instead of `AmazonS3FullAccess`, create a custom policy with minimal permissions:

1. In IAM, go to "Policies" → "Create policy"
2. Click "JSON" tab and paste:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::YOUR-BUCKET-NAME/*",
                "arn:aws:s3:::YOUR-BUCKET-NAME"
            ]
        }
    ]
}
```

3. Replace `YOUR-BUCKET-NAME` with your actual bucket name
4. Click "Next"
5. Name it `VideoSchedulerS3Policy`
6. Click "Create policy"
7. Attach this policy to your IAM user

## Step 4: Configure Your Application

1. **Check your `.env` file**

```bash
cd multi-platform-scheduler/backend
cat .env
```

2. **Update the `.env` file with your AWS credentials**

```bash
# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_access_key_id_here
AWS_SECRET_ACCESS_KEY=your_secret_access_key_here
AWS_REGION=us-east-1
AWS_S3_BUCKET=my-video-scheduler-videos
```

Replace:
- `your_access_key_id_here` with your Access Key ID
- `your_secret_access_key_here` with your Secret Access Key
- `us-east-1` with your chosen region
- `my-video-scheduler-videos` with your bucket name

3. **Restart the backend server**

```bash
# Stop the current server
pkill -f "uvicorn main:app"

# Start it again
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
```

## Step 5: Test the Setup

1. **Test S3 connection from backend**

```bash
cd multi-platform-scheduler/backend
source venv/bin/activate
python3 << 'EOF'
import boto3
from src.config import settings

# Create S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    region_name=settings.aws_region
)

# Test connection
try:
    response = s3_client.list_objects_v2(
        Bucket=settings.aws_s3_bucket,
        MaxKeys=1
    )
    print("✅ S3 connection successful!")
    print(f"Bucket: {settings.aws_s3_bucket}")
    print(f"Region: {settings.aws_region}")
except Exception as e:
    print(f"❌ S3 connection failed: {e}")
EOF
```

2. **Test video upload in the UI**
   - Go to http://localhost:3000/dashboard/videos
   - Click "Upload Video"
   - Select a video file
   - Upload should work!

## Troubleshooting

### Error: "Access Denied"
- Check that your IAM user has the correct permissions
- Verify your AWS credentials in `.env` are correct
- Ensure the bucket name matches exactly

### Error: "Bucket does not exist"
- Verify the bucket name in `.env` matches your S3 bucket
- Check that you're using the correct AWS region

### Error: "CORS policy"
- Make sure you configured CORS on your S3 bucket
- Verify the AllowedOrigins includes your frontend URL

### Error: "Invalid credentials"
- Double-check your AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
- Make sure there are no extra spaces or quotes
- Verify the IAM user has access keys created

## Cost Considerations

AWS S3 pricing (as of 2024):
- **Storage**: ~$0.023 per GB/month for first 50 TB
- **PUT requests**: $0.005 per 1,000 requests
- **GET requests**: $0.0004 per 1,000 requests
- **Data transfer out**: First 100 GB/month free, then $0.09/GB

**Estimated costs for testing**:
- 10 GB storage: ~$0.23/month
- 1,000 uploads: ~$0.005
- 10,000 downloads: ~$0.004

**Total for light testing**: Less than $1/month

## Security Best Practices

1. **Never commit AWS credentials to git**
   - `.env` is already in `.gitignore`
   - Use environment variables in production

2. **Use IAM roles in production**
   - When deploying to AWS (EC2, ECS, Lambda), use IAM roles instead of access keys

3. **Enable bucket versioning** (optional)
   - Protects against accidental deletions
   - Can be enabled in bucket settings

4. **Set up lifecycle policies** (optional)
   - Automatically delete old videos after X days
   - Move to cheaper storage classes (Glacier) for archives

5. **Monitor costs**
   - Set up AWS Budgets to alert you if costs exceed expectations
   - Review S3 usage regularly in AWS Cost Explorer

## Next Steps

Once S3 is configured:
1. Test video uploads in the UI
2. Verify videos are stored in your S3 bucket
3. Test video playback and downloads
4. Configure social media platform credentials for posting

## Additional Resources

- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [S3 Pricing Calculator](https://calculator.aws/)
