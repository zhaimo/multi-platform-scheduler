# Environment Variables Reference

This document provides a comprehensive reference for all environment variables used in the Multi-Platform Video Scheduler application.

## Table of Contents

- [Backend Environment Variables](#backend-environment-variables)
- [Frontend Environment Variables](#frontend-environment-variables)
- [Worker Environment Variables](#worker-environment-variables)
- [Environment-Specific Configurations](#environment-specific-configurations)

---

## Backend Environment Variables

### Application Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_NAME` | No | `Multi-Platform Scheduler` | Application name for logging and monitoring |
| `APP_ENV` | Yes | - | Environment: `development`, `staging`, `production` |
| `DEBUG` | No | `false` | Enable debug mode (set to `true` only in development) |
| `LOG_LEVEL` | No | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `API_HOST` | No | `0.0.0.0` | Host to bind the API server |
| `API_PORT` | No | `8000` | Port for the API server |

### Database Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string: `postgresql://user:password@host:port/dbname` |
| `DATABASE_POOL_SIZE` | No | `10` | Maximum number of database connections in the pool |
| `DATABASE_MAX_OVERFLOW` | No | `20` | Maximum overflow connections beyond pool_size |
| `DATABASE_POOL_TIMEOUT` | No | `30` | Timeout in seconds for getting a connection from the pool |

**Example:**
```bash
DATABASE_URL=postgresql://scheduler_user:secure_password@localhost:5432/scheduler_db
```

### Redis Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | Yes | - | Redis connection string: `redis://host:port/db` |
| `REDIS_PASSWORD` | No | - | Redis password (if authentication is enabled) |
| `CELERY_BROKER_URL` | Yes | - | Celery broker URL (typically same as REDIS_URL) |
| `CELERY_RESULT_BACKEND` | Yes | - | Celery result backend URL |

**Example:**
```bash
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### AWS S3 Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AWS_ACCESS_KEY_ID` | Yes | - | AWS access key for S3 access |
| `AWS_SECRET_ACCESS_KEY` | Yes | - | AWS secret key for S3 access |
| `AWS_REGION` | Yes | - | AWS region (e.g., `us-east-1`) |
| `S3_BUCKET_NAME` | Yes | - | S3 bucket name for video storage |
| `S3_UPLOAD_EXPIRATION` | No | `3600` | Pre-signed URL expiration in seconds (default: 1 hour) |

**Example:**
```bash
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
S3_BUCKET_NAME=my-video-scheduler-bucket
```

### JWT Authentication

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET_KEY` | Yes | - | Secret key for signing JWT tokens (use a strong random string) |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | No | `15` | Access token expiration time in minutes |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | Refresh token expiration time in days |

**Example:**
```bash
JWT_SECRET_KEY=your-super-secret-key-change-this-in-production-min-32-chars
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

**Security Note:** Generate a secure random key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Encryption

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENCRYPTION_KEY` | Yes | - | AES-256 encryption key for platform tokens (32 bytes base64-encoded) |

**Example:**
```bash
ENCRYPTION_KEY=your-base64-encoded-32-byte-key-here
```

**Generate encryption key:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Platform API Credentials

#### TikTok

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TIKTOK_CLIENT_KEY` | Yes | - | TikTok app client key |
| `TIKTOK_CLIENT_SECRET` | Yes | - | TikTok app client secret |
| `TIKTOK_REDIRECT_URI` | Yes | - | OAuth redirect URI (must match TikTok app settings) |

#### YouTube

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `YOUTUBE_CLIENT_ID` | Yes | - | Google OAuth client ID |
| `YOUTUBE_CLIENT_SECRET` | Yes | - | Google OAuth client secret |
| `YOUTUBE_REDIRECT_URI` | Yes | - | OAuth redirect URI |

#### Instagram

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `INSTAGRAM_APP_ID` | Yes | - | Instagram/Facebook app ID |
| `INSTAGRAM_APP_SECRET` | Yes | - | Instagram/Facebook app secret |
| `INSTAGRAM_REDIRECT_URI` | Yes | - | OAuth redirect URI |

#### Facebook

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FACEBOOK_APP_ID` | Yes | - | Facebook app ID |
| `FACEBOOK_APP_SECRET` | Yes | - | Facebook app secret |
| `FACEBOOK_REDIRECT_URI` | Yes | - | OAuth redirect URI |

### Email/Notification Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SMTP_HOST` | No | - | SMTP server host for email notifications |
| `SMTP_PORT` | No | `587` | SMTP server port |
| `SMTP_USER` | No | - | SMTP username |
| `SMTP_PASSWORD` | No | - | SMTP password |
| `SMTP_FROM_EMAIL` | No | - | From email address for notifications |
| `SMTP_USE_TLS` | No | `true` | Use TLS for SMTP connection |

**Alternative: SendGrid**
```bash
SENDGRID_API_KEY=your-sendgrid-api-key
SENDGRID_FROM_EMAIL=noreply@yourdomain.com
```

### Monitoring & Error Tracking

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SENTRY_DSN` | No | - | Sentry DSN for error tracking |
| `SENTRY_ENVIRONMENT` | No | - | Sentry environment tag |
| `SENTRY_TRACES_SAMPLE_RATE` | No | `0.1` | Percentage of transactions to trace (0.0 to 1.0) |

### CORS Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CORS_ORIGINS` | Yes | - | Comma-separated list of allowed origins |
| `CORS_ALLOW_CREDENTIALS` | No | `true` | Allow credentials in CORS requests |

**Example:**
```bash
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

### Rate Limiting

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RATE_LIMIT_PER_MINUTE` | No | `100` | Maximum requests per minute per user |
| `RATE_LIMIT_ENABLED` | No | `true` | Enable/disable rate limiting |

---

## Frontend Environment Variables

All frontend environment variables must be prefixed with `NEXT_PUBLIC_` to be accessible in the browser.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | Yes | - | Backend API URL (e.g., `http://localhost:8000` or `https://api.yourdomain.com`) |
| `NEXT_PUBLIC_APP_NAME` | No | `Video Scheduler` | Application name displayed in UI |
| `NEXT_PUBLIC_SENTRY_DSN` | No | - | Sentry DSN for frontend error tracking |

**Example (.env.local):**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=Multi-Platform Video Scheduler
```

---

## Worker Environment Variables

Celery workers use the same environment variables as the backend, with additional worker-specific settings:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CELERY_WORKER_CONCURRENCY` | No | `4` | Number of concurrent worker processes |
| `CELERY_WORKER_PREFETCH_MULTIPLIER` | No | `4` | Number of tasks to prefetch per worker |
| `CELERY_TASK_TIME_LIMIT` | No | `3600` | Hard time limit for tasks in seconds |
| `CELERY_TASK_SOFT_TIME_LIMIT` | No | `3000` | Soft time limit for tasks in seconds |

---

## Environment-Specific Configurations

### Development (.env.development)

```bash
# Application
APP_ENV=development
DEBUG=true
LOG_LEVEL=DEBUG

# Database
DATABASE_URL=postgresql://scheduler_user:password@localhost:5432/scheduler_dev

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# AWS (use localstack or test bucket)
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_REGION=us-east-1
S3_BUCKET_NAME=scheduler-dev-bucket

# JWT
JWT_SECRET_KEY=dev-secret-key-change-in-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# Encryption
ENCRYPTION_KEY=dev-encryption-key-base64

# CORS
CORS_ORIGINS=http://localhost:3000

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Staging (.env.staging)

```bash
# Application
APP_ENV=staging
DEBUG=false
LOG_LEVEL=INFO

# Database (use managed PostgreSQL)
DATABASE_URL=postgresql://user:password@staging-db.example.com:5432/scheduler_staging

# Redis (use managed Redis)
REDIS_URL=redis://staging-redis.example.com:6379/0
CELERY_BROKER_URL=redis://staging-redis.example.com:6379/0
CELERY_RESULT_BACKEND=redis://staging-redis.example.com:6379/0

# AWS
AWS_ACCESS_KEY_ID=<staging-access-key>
AWS_SECRET_ACCESS_KEY=<staging-secret-key>
AWS_REGION=us-east-1
S3_BUCKET_NAME=scheduler-staging-bucket

# JWT (use strong keys)
JWT_SECRET_KEY=<generated-secret-key>
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15

# Encryption
ENCRYPTION_KEY=<generated-encryption-key>

# Platform APIs (use test/sandbox credentials)
TIKTOK_CLIENT_KEY=<staging-client-key>
TIKTOK_CLIENT_SECRET=<staging-client-secret>
TIKTOK_REDIRECT_URI=https://staging.yourdomain.com/api/auth/platforms/tiktok/callback

# CORS
CORS_ORIGINS=https://staging.yourdomain.com

# Monitoring
SENTRY_DSN=<your-sentry-dsn>
SENTRY_ENVIRONMENT=staging

# Frontend
NEXT_PUBLIC_API_URL=https://api-staging.yourdomain.com
```

### Production (.env.production)

```bash
# Application
APP_ENV=production
DEBUG=false
LOG_LEVEL=WARNING

# Database (use managed PostgreSQL with SSL)
DATABASE_URL=postgresql://user:password@prod-db.example.com:5432/scheduler_prod?sslmode=require
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Redis (use managed Redis with password)
REDIS_URL=redis://:password@prod-redis.example.com:6379/0
CELERY_BROKER_URL=redis://:password@prod-redis.example.com:6379/0
CELERY_RESULT_BACKEND=redis://:password@prod-redis.example.com:6379/0

# AWS
AWS_ACCESS_KEY_ID=<production-access-key>
AWS_SECRET_ACCESS_KEY=<production-secret-key>
AWS_REGION=us-east-1
S3_BUCKET_NAME=scheduler-production-bucket

# JWT (use strong keys)
JWT_SECRET_KEY=<strong-generated-secret-key>
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Encryption
ENCRYPTION_KEY=<strong-generated-encryption-key>

# Platform APIs (use production credentials)
TIKTOK_CLIENT_KEY=<production-client-key>
TIKTOK_CLIENT_SECRET=<production-client-secret>
TIKTOK_REDIRECT_URI=https://yourdomain.com/api/auth/platforms/tiktok/callback

YOUTUBE_CLIENT_ID=<production-client-id>
YOUTUBE_CLIENT_SECRET=<production-client-secret>
YOUTUBE_REDIRECT_URI=https://yourdomain.com/api/auth/platforms/youtube/callback

INSTAGRAM_APP_ID=<production-app-id>
INSTAGRAM_APP_SECRET=<production-app-secret>
INSTAGRAM_REDIRECT_URI=https://yourdomain.com/api/auth/platforms/instagram/callback

FACEBOOK_APP_ID=<production-app-id>
FACEBOOK_APP_SECRET=<production-app-secret>
FACEBOOK_REDIRECT_URI=https://yourdomain.com/api/auth/platforms/facebook/callback

# Email
SENDGRID_API_KEY=<your-sendgrid-api-key>
SENDGRID_FROM_EMAIL=noreply@yourdomain.com

# CORS
CORS_ORIGINS=https://yourdomain.com

# Monitoring
SENTRY_DSN=<your-sentry-dsn>
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_ENABLED=true

# Frontend
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_SENTRY_DSN=<your-frontend-sentry-dsn>
```

---

## Security Best Practices

1. **Never commit .env files to version control**
   - Add `.env*` to `.gitignore` (except `.env.example`)
   
2. **Use strong random keys**
   - Generate JWT secrets and encryption keys using cryptographically secure methods
   - Minimum 32 characters for secrets

3. **Rotate credentials regularly**
   - Change JWT secrets, encryption keys, and API credentials periodically
   - Update all platform API credentials when rotating

4. **Use environment-specific credentials**
   - Never use production credentials in development or staging
   - Use separate AWS accounts/buckets for each environment

5. **Secure credential storage**
   - Use AWS Secrets Manager, HashiCorp Vault, or similar for production
   - Never log or expose sensitive environment variables

6. **Validate required variables on startup**
   - The application will fail to start if required variables are missing
   - Check logs for configuration errors

---

## Validation

To validate your environment configuration, run:

```bash
# Backend
cd backend
python -c "from src.config import settings; print('Configuration valid!')"

# Frontend
cd frontend
npm run build
```

If configuration is invalid, you'll see specific error messages indicating which variables are missing or incorrect.
