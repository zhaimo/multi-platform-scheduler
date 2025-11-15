# Deployment Guide

This guide provides step-by-step instructions for deploying the Multi-Platform Video Scheduler to AWS and Vercel.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Deployment Architecture](#deployment-architecture)
- [AWS Deployment](#aws-deployment)
- [Vercel Deployment (Frontend)](#vercel-deployment-frontend)
- [Alternative: Docker Compose Deployment](#alternative-docker-compose-deployment)
- [Post-Deployment Configuration](#post-deployment-configuration)
- [Monitoring and Maintenance](#monitoring-and-maintenance)

---

## Prerequisites

### Required Accounts

- AWS account with appropriate permissions
- Vercel account (for frontend deployment)
- Domain name (optional but recommended)
- Platform developer accounts:
  - TikTok Developer Account
  - Google Cloud Console (YouTube)
  - Meta Developer Account (Instagram/Facebook)

### Required Tools

- AWS CLI configured with credentials
- Docker and Docker Compose
- Node.js 18+ and npm
- Python 3.11+
- Git

### Required Services

- PostgreSQL database (AWS RDS recommended)
- Redis instance (AWS ElastiCache recommended)
- S3 bucket for video storage
- SMTP service or SendGrid account

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     AWS Cloud                           │
│                                                         │
│  ┌──────────────┐      ┌──────────────┐               │
│  │   ECS/EKS    │      │  ElastiCache │               │
│  │   Backend    │◄────►│    Redis     │               │
│  │   + Workers  │      └──────────────┘               │
│  └──────┬───────┘                                      │
│         │                                              │
│         ▼                                              │
│  ┌──────────────┐      ┌──────────────┐               │
│  │   RDS        │      │      S3      │               │
│  │  PostgreSQL  │      │    Bucket    │               │
│  └──────────────┘      └──────────────┘               │
│                                                         │
│  ┌──────────────┐                                      │
│  │ CloudWatch   │  (Monitoring & Logs)                │
│  └──────────────┘                                      │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │     Vercel      │
                  │  Next.js        │
                  │  Frontend       │
                  └─────────────────┘
```

---

## AWS Deployment

### Step 1: Set Up AWS Infrastructure

#### 1.1 Create VPC and Networking

```bash
# Create VPC
aws ec2 create-vpc --cidr-block 10.0.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=scheduler-vpc}]'

# Create subnets (at least 2 for RDS)
aws ec2 create-subnet --vpc-id <vpc-id> --cidr-block 10.0.1.0/24 --availability-zone us-east-1a
aws ec2 create-subnet --vpc-id <vpc-id> --cidr-block 10.0.2.0/24 --availability-zone us-east-1b

# Create Internet Gateway
aws ec2 create-internet-gateway --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=scheduler-igw}]'
aws ec2 attach-internet-gateway --vpc-id <vpc-id> --internet-gateway-id <igw-id>
```

#### 1.2 Create RDS PostgreSQL Database

```bash
# Create DB subnet group
aws rds create-db-subnet-group \
  --db-subnet-group-name scheduler-db-subnet \
  --db-subnet-group-description "Scheduler DB Subnet Group" \
  --subnet-ids <subnet-id-1> <subnet-id-2>

# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier scheduler-db-prod \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 15.4 \
  --master-username scheduler_admin \
  --master-user-password <strong-password> \
  --allocated-storage 100 \
  --storage-type gp3 \
  --db-subnet-group-name scheduler-db-subnet \
  --vpc-security-group-ids <security-group-id> \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "mon:04:00-mon:05:00" \
  --multi-az \
  --publicly-accessible false \
  --storage-encrypted \
  --enable-performance-insights
```

**Wait for database to be available:**
```bash
aws rds wait db-instance-available --db-instance-identifier scheduler-db-prod
```

**Get database endpoint:**
```bash
aws rds describe-db-instances --db-instance-identifier scheduler-db-prod \
  --query 'DBInstances[0].Endpoint.Address' --output text
```

#### 1.3 Create ElastiCache Redis

```bash
# Create cache subnet group
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name scheduler-redis-subnet \
  --cache-subnet-group-description "Scheduler Redis Subnet Group" \
  --subnet-ids <subnet-id-1> <subnet-id-2>

# Create Redis cluster
aws elasticache create-replication-group \
  --replication-group-id scheduler-redis-prod \
  --replication-group-description "Scheduler Redis Cluster" \
  --engine redis \
  --cache-node-type cache.t3.medium \
  --num-cache-clusters 2 \
  --automatic-failover-enabled \
  --cache-subnet-group-name scheduler-redis-subnet \
  --security-group-ids <security-group-id> \
  --at-rest-encryption-enabled \
  --transit-encryption-enabled \
  --auth-token <strong-auth-token>
```

**Get Redis endpoint:**
```bash
aws elasticache describe-replication-groups \
  --replication-group-id scheduler-redis-prod \
  --query 'ReplicationGroups[0].NodeGroups[0].PrimaryEndpoint.Address' --output text
```

#### 1.4 Create S3 Bucket

```bash
# Create bucket
aws s3 mb s3://scheduler-videos-prod --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket scheduler-videos-prod \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket scheduler-videos-prod \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Set lifecycle policy (optional - delete old videos after 90 days)
aws s3api put-bucket-lifecycle-configuration \
  --bucket scheduler-videos-prod \
  --lifecycle-configuration file://s3-lifecycle.json
```

**s3-lifecycle.json:**
```json
{
  "Rules": [
    {
      "Id": "DeleteOldVideos",
      "Status": "Enabled",
      "Prefix": "",
      "Expiration": {
        "Days": 90
      }
    }
  ]
}
```

#### 1.5 Create IAM Role for ECS Tasks

```bash
# Create trust policy
cat > ecs-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create role
aws iam create-role \
  --role-name scheduler-ecs-task-role \
  --assume-role-policy-document file://ecs-trust-policy.json

# Attach S3 policy
cat > s3-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::scheduler-videos-prod",
        "arn:aws:s3:::scheduler-videos-prod/*"
      ]
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name scheduler-ecs-task-role \
  --policy-name S3Access \
  --policy-document file://s3-policy.json
```

### Step 2: Deploy Backend to ECS

#### 2.1 Build and Push Docker Images

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Create ECR repositories
aws ecr create-repository --repository-name scheduler-backend
aws ecr create-repository --repository-name scheduler-worker

# Build and push backend
cd backend
docker build -f Dockerfile.prod -t scheduler-backend:latest .
docker tag scheduler-backend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/scheduler-backend:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/scheduler-backend:latest

# Build and push worker
docker build -f Dockerfile.worker -t scheduler-worker:latest .
docker tag scheduler-worker:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/scheduler-worker:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/scheduler-worker:latest
```

#### 2.2 Create ECS Cluster

```bash
aws ecs create-cluster --cluster-name scheduler-prod-cluster
```

#### 2.3 Create Task Definitions

**backend-task-definition.json:**
```json
{
  "family": "scheduler-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "taskRoleArn": "arn:aws:iam::<account-id>:role/scheduler-ecs-task-role",
  "executionRoleArn": "arn:aws:iam::<account-id>:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/scheduler-backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "APP_ENV", "value": "production"},
        {"name": "LOG_LEVEL", "value": "INFO"}
      ],
      "secrets": [
        {"name": "DATABASE_URL", "valueFrom": "arn:aws:secretsmanager:us-east-1:<account-id>:secret:scheduler/database-url"},
        {"name": "REDIS_URL", "valueFrom": "arn:aws:secretsmanager:us-east-1:<account-id>:secret:scheduler/redis-url"},
        {"name": "JWT_SECRET_KEY", "valueFrom": "arn:aws:secretsmanager:us-east-1:<account-id>:secret:scheduler/jwt-secret"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/scheduler-backend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

Register task definition:
```bash
aws ecs register-task-definition --cli-input-json file://backend-task-definition.json
```

#### 2.4 Create Application Load Balancer

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name scheduler-alb \
  --subnets <subnet-id-1> <subnet-id-2> \
  --security-groups <security-group-id> \
  --scheme internet-facing \
  --type application

# Create target group
aws elbv2 create-target-group \
  --name scheduler-backend-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id <vpc-id> \
  --target-type ip \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3

# Create listener
aws elbv2 create-listener \
  --load-balancer-arn <alb-arn> \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=<certificate-arn> \
  --default-actions Type=forward,TargetGroupArn=<target-group-arn>
```

#### 2.5 Create ECS Service

```bash
aws ecs create-service \
  --cluster scheduler-prod-cluster \
  --service-name scheduler-backend-service \
  --task-definition scheduler-backend \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<subnet-id-1>,<subnet-id-2>],securityGroups=[<security-group-id>],assignPublicIp=DISABLED}" \
  --load-balancers "targetGroupArn=<target-group-arn>,containerName=backend,containerPort=8000" \
  --health-check-grace-period-seconds 60
```

#### 2.6 Deploy Celery Workers

Create worker task definition (similar to backend but without load balancer) and service:

```bash
aws ecs create-service \
  --cluster scheduler-prod-cluster \
  --service-name scheduler-worker-service \
  --task-definition scheduler-worker \
  --desired-count 3 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<subnet-id-1>,<subnet-id-2>],securityGroups=[<security-group-id>],assignPublicIp=DISABLED}"
```

### Step 3: Run Database Migrations

```bash
# Connect to ECS task
aws ecs execute-command \
  --cluster scheduler-prod-cluster \
  --task <task-id> \
  --container backend \
  --interactive \
  --command "/bin/bash"

# Inside container
alembic upgrade head
```

### Step 4: Configure Secrets Manager

```bash
# Store database URL
aws secretsmanager create-secret \
  --name scheduler/database-url \
  --secret-string "postgresql://user:password@<rds-endpoint>:5432/scheduler_prod"

# Store Redis URL
aws secretsmanager create-secret \
  --name scheduler/redis-url \
  --secret-string "redis://:auth-token@<redis-endpoint>:6379/0"

# Store JWT secret
aws secretsmanager create-secret \
  --name scheduler/jwt-secret \
  --secret-string "<generated-jwt-secret>"

# Store encryption key
aws secretsmanager create-secret \
  --name scheduler/encryption-key \
  --secret-string "<generated-encryption-key>"

# Store platform credentials
aws secretsmanager create-secret \
  --name scheduler/tiktok-credentials \
  --secret-string '{"client_key":"xxx","client_secret":"xxx"}'
```

---

## Vercel Deployment (Frontend)

### Step 1: Prepare Frontend

```bash
cd frontend

# Install dependencies
npm install

# Build to verify
npm run build
```

### Step 2: Deploy to Vercel

#### Option A: Using Vercel CLI

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy
vercel --prod
```

#### Option B: Using Vercel Dashboard

1. Go to [vercel.com](https://vercel.com)
2. Click "Add New Project"
3. Import your Git repository
4. Configure:
   - Framework Preset: Next.js
   - Root Directory: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `.next`

### Step 3: Configure Environment Variables

In Vercel dashboard, add environment variables:

```
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_APP_NAME=Multi-Platform Video Scheduler
NEXT_PUBLIC_SENTRY_DSN=<your-sentry-dsn>
```

### Step 4: Configure Custom Domain

1. In Vercel dashboard, go to Settings → Domains
2. Add your custom domain
3. Configure DNS records as instructed
4. Wait for SSL certificate provisioning

---

## Alternative: Docker Compose Deployment

For smaller deployments or self-hosting:

### Step 1: Prepare Server

```bash
# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Step 2: Clone Repository

```bash
git clone <your-repo-url>
cd multi-platform-scheduler
```

### Step 3: Configure Environment

```bash
# Copy and edit environment files
cp backend/.env.production.example backend/.env
cp frontend/.env.example frontend/.env.local

# Edit with your values
nano backend/.env
nano frontend/.env.local
```

### Step 4: Deploy

```bash
# Build and start services
docker-compose -f docker-compose.prod.yml up -d

# Run migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Check logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Step 5: Configure Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/scheduler
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/scheduler /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Post-Deployment Configuration

### 1. Configure Platform OAuth Redirect URIs

Update redirect URIs in each platform's developer console:

- **TikTok**: https://yourdomain.com/api/auth/platforms/tiktok/callback
- **YouTube**: https://yourdomain.com/api/auth/platforms/youtube/callback
- **Instagram**: https://yourdomain.com/api/auth/platforms/instagram/callback
- **Facebook**: https://yourdomain.com/api/auth/platforms/facebook/callback

### 2. Set Up SSL Certificates

For AWS ALB:
```bash
# Request certificate in ACM
aws acm request-certificate \
  --domain-name yourdomain.com \
  --subject-alternative-names www.yourdomain.com api.yourdomain.com \
  --validation-method DNS
```

For Docker Compose deployment:
```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### 3. Configure DNS

Point your domain to the deployment:

```
# For AWS
api.yourdomain.com    CNAME    <alb-dns-name>

# For Vercel
yourdomain.com        CNAME    cname.vercel-dns.com
www.yourdomain.com    CNAME    cname.vercel-dns.com

# For Docker Compose
yourdomain.com        A        <server-ip>
```

### 4. Set Up Monitoring

Configure CloudWatch alarms (AWS) or monitoring tools:

```bash
# CPU utilization alarm
aws cloudwatch put-metric-alarm \
  --alarm-name scheduler-high-cpu \
  --alarm-description "Alert when CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2

# Memory utilization alarm
aws cloudwatch put-metric-alarm \
  --alarm-name scheduler-high-memory \
  --alarm-description "Alert when memory exceeds 80%" \
  --metric-name MemoryUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

### 5. Verify Deployment

```bash
# Check health endpoint
curl https://api.yourdomain.com/health

# Expected response:
# {"status":"healthy","database":"connected","redis":"connected"}

# Check frontend
curl https://yourdomain.com

# Test authentication
curl -X POST https://api.yourdomain.com/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPassword123!"}'
```

---

## Monitoring and Maintenance

### Daily Checks

- Monitor error rates in Sentry
- Check CloudWatch logs for errors
- Verify scheduled posts are executing
- Monitor S3 storage usage

### Weekly Tasks

- Review performance metrics
- Check database query performance
- Review and rotate logs
- Update dependencies if needed

### Monthly Tasks

- Review and optimize costs
- Update platform API credentials if needed
- Review and update security groups
- Backup database (automated but verify)

### Scaling Guidelines

**Scale up when:**
- CPU utilization > 70% consistently
- Memory utilization > 80%
- Request latency > 500ms
- Queue depth > 1000 jobs

**Scaling actions:**
```bash
# Scale ECS service
aws ecs update-service \
  --cluster scheduler-prod-cluster \
  --service scheduler-backend-service \
  --desired-count 4

# Scale workers
aws ecs update-service \
  --cluster scheduler-prod-cluster \
  --service scheduler-worker-service \
  --desired-count 6
```

---

## Rollback Procedure

If deployment fails:

### ECS Rollback

```bash
# List task definitions
aws ecs list-task-definitions --family-prefix scheduler-backend

# Update service to previous version
aws ecs update-service \
  --cluster scheduler-prod-cluster \
  --service scheduler-backend-service \
  --task-definition scheduler-backend:<previous-revision>
```

### Vercel Rollback

1. Go to Vercel dashboard
2. Navigate to Deployments
3. Find previous successful deployment
4. Click "Promote to Production"

### Database Rollback

```bash
# Downgrade migration
docker-compose exec backend alembic downgrade -1

# Or to specific revision
docker-compose exec backend alembic downgrade <revision-id>
```

---

## Support and Resources

- AWS Documentation: https://docs.aws.amazon.com/
- Vercel Documentation: https://vercel.com/docs
- FastAPI Documentation: https://fastapi.tiangolo.com/
- Next.js Documentation: https://nextjs.org/docs

For issues, check the [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) guide.
