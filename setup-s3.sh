#!/bin/bash

# AWS S3 Setup Script for Multi-Platform Video Scheduler
# This script helps you configure AWS S3 credentials

echo "🚀 AWS S3 Setup for Multi-Platform Video Scheduler"
echo "=================================================="
echo ""

# Check if .env exists
if [ ! -f "backend/.env" ]; then
    echo "❌ Error: backend/.env file not found!"
    echo "Please create it first by copying .env.example"
    exit 1
fi

echo "This script will help you configure AWS S3 for video storage."
echo ""
echo "Before proceeding, make sure you have:"
echo "  1. Created an AWS account"
echo "  2. Created an S3 bucket"
echo "  3. Created an IAM user with S3 access"
echo "  4. Generated access keys for the IAM user"
echo ""
echo "📖 See AWS_S3_SETUP.md for detailed instructions"
echo ""

read -p "Do you have your AWS credentials ready? (y/n): " ready

if [ "$ready" != "y" ] && [ "$ready" != "Y" ]; then
    echo ""
    echo "Please follow the guide in AWS_S3_SETUP.md to set up AWS S3 first."
    echo "Then run this script again."
    exit 0
fi

echo ""
echo "Great! Let's configure your AWS S3 settings."
echo ""

# Get AWS credentials
read -p "Enter your AWS Access Key ID: " aws_access_key
read -p "Enter your AWS Secret Access Key: " aws_secret_key
read -p "Enter your AWS Region (e.g., us-east-1): " aws_region
read -p "Enter your S3 Bucket Name: " s3_bucket

echo ""
echo "Updating backend/.env file..."

# Update .env file
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s|AWS_ACCESS_KEY_ID=.*|AWS_ACCESS_KEY_ID=$aws_access_key|" backend/.env
    sed -i '' "s|AWS_SECRET_ACCESS_KEY=.*|AWS_SECRET_ACCESS_KEY=$aws_secret_key|" backend/.env
    sed -i '' "s|AWS_REGION=.*|AWS_REGION=$aws_region|" backend/.env
    sed -i '' "s|S3_BUCKET_NAME=.*|S3_BUCKET_NAME=$s3_bucket|" backend/.env
else
    # Linux
    sed -i "s|AWS_ACCESS_KEY_ID=.*|AWS_ACCESS_KEY_ID=$aws_access_key|" backend/.env
    sed -i "s|AWS_SECRET_ACCESS_KEY=.*|AWS_SECRET_ACCESS_KEY=$aws_secret_key|" backend/.env
    sed -i "s|AWS_REGION=.*|AWS_REGION=$aws_region|" backend/.env
    sed -i "s|S3_BUCKET_NAME=.*|S3_BUCKET_NAME=$s3_bucket|" backend/.env
fi

echo "✅ Configuration updated!"
echo ""

# Test connection
echo "Testing AWS S3 connection..."
echo ""

cd backend
source venv/bin/activate

python3 << EOF
import boto3
import sys

try:
    s3_client = boto3.client(
        's3',
        aws_access_key_id='$aws_access_key',
        aws_secret_access_key='$aws_secret_key',
        region_name='$aws_region'
    )
    
    # Test connection
    response = s3_client.list_objects_v2(
        Bucket='$s3_bucket',
        MaxKeys=1
    )
    
    print("✅ SUCCESS! S3 connection is working!")
    print(f"   Bucket: $s3_bucket")
    print(f"   Region: $aws_region")
    print("")
    sys.exit(0)
    
except Exception as e:
    print(f"❌ ERROR: Failed to connect to S3")
    print(f"   {str(e)}")
    print("")
    print("Please check:")
    print("  1. Your AWS credentials are correct")
    print("  2. The bucket name is correct")
    print("  3. The IAM user has S3 permissions")
    print("  4. The bucket exists in the specified region")
    print("")
    sys.exit(1)
EOF

test_result=$?

cd ..

if [ $test_result -eq 0 ]; then
    echo "🎉 AWS S3 is configured and working!"
    echo ""
    echo "Next steps:"
    echo "  1. Restart your backend server"
    echo "  2. Go to http://localhost:3000/dashboard/videos"
    echo "  3. Try uploading a video!"
    echo ""
    
    read -p "Would you like to restart the backend server now? (y/n): " restart
    
    if [ "$restart" = "y" ] || [ "$restart" = "Y" ]; then
        echo ""
        echo "Restarting backend server..."
        pkill -f "uvicorn main:app"
        sleep 2
        cd backend
        source venv/bin/activate
        uvicorn main:app --reload --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
        echo "✅ Backend server restarted!"
        echo "   Check logs: tail -f /tmp/backend.log"
    fi
else
    echo "⚠️  Configuration saved but connection test failed."
    echo "Please review the error above and check AWS_S3_SETUP.md for troubleshooting."
fi

echo ""
echo "Done!"
