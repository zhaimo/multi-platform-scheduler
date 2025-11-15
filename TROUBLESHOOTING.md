# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the Multi-Platform Video Scheduler.

## Table of Contents

- [Application Won't Start](#application-wont-start)
- [Database Connection Issues](#database-connection-issues)
- [Redis/Celery Issues](#rediscelery-issues)
- [Authentication Problems](#authentication-problems)
- [Platform API Issues](#platform-api-issues)
- [Video Upload Problems](#video-upload-problems)
- [Posting Failures](#posting-failures)
- [Performance Issues](#performance-issues)
- [Frontend Issues](#frontend-issues)
- [Docker Issues](#docker-issues)
- [Common Error Messages](#common-error-messages)

---

## Application Won't Start

### Backend fails to start

**Symptoms:**
- Container exits immediately
- "Configuration error" in logs
- Import errors

**Diagnosis:**
```bash
# Check logs
docker-compose logs backend

# Or for ECS
aws logs tail /ecs/scheduler-backend --follow
```

**Common Causes:**

#### 1. Missing Environment Variables

**Error:**
```
ValidationError: 1 validation error for Settings
DATABASE_URL
  field required
```

**Solution:**
```bash
# Check .env file exists
ls -la backend/.env

# Verify required variables
cat backend/.env | grep DATABASE_URL

# Copy from example if missing
cp backend/.env.example backend/.env
```

#### 2. Invalid Database URL Format

**Error:**
```
sqlalchemy.exc.ArgumentError: Could not parse SQLAlchemy URL from string
```

**Solution:**
```bash
# Correct format
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Common mistakes:
# ❌ postgres:// (should be postgresql://)
# ❌ Missing port
# ❌ Special characters in password not URL-encoded
```

#### 3. Python Import Errors

**Error:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution:**
```bash
# Reinstall dependencies
cd backend
pip install -r requirements.txt

# Or rebuild Docker image
docker-compose build backend
```

### Frontend fails to start

**Symptoms:**
- Build errors
- Module not found errors
- Port already in use

**Diagnosis:**
```bash
# Check logs
docker-compose logs frontend

# Or locally
cd frontend
npm run dev
```

**Common Causes:**

#### 1. Missing Dependencies

**Error:**
```
Error: Cannot find module 'next'
```

**Solution:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

#### 2. Port Conflict

**Error:**
```
Error: Port 3000 is already in use
```

**Solution:**
```bash
# Find process using port
lsof -i :3000

# Kill process
kill -9 <PID>

# Or use different port
PORT=3001 npm run dev
```

#### 3. Environment Variable Issues

**Error:**
```
Error: NEXT_PUBLIC_API_URL is not defined
```

**Solution:**
```bash
# Create .env.local
cat > frontend/.env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF
```

---

## Database Connection Issues

### Cannot connect to PostgreSQL

**Symptoms:**
- "Connection refused" errors
- Timeout errors
- Authentication failures

**Diagnosis:**
```bash
# Test connection manually
psql -h localhost -U scheduler_user -d scheduler_db

# Or using Docker
docker-compose exec backend python -c "from src.database import engine; print(engine.connect())"
```

**Common Causes:**

#### 1. Database Not Running

**Solution:**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Start if stopped
docker-compose up -d postgres

# Check logs
docker-compose logs postgres
```

#### 2. Wrong Credentials

**Error:**
```
psycopg2.OperationalError: FATAL: password authentication failed for user "scheduler_user"
```

**Solution:**
```bash
# Verify credentials in .env match docker-compose.yml
grep DATABASE_URL backend/.env
grep POSTGRES_PASSWORD docker-compose.yml

# Reset database if needed
docker-compose down -v
docker-compose up -d postgres
```

#### 3. Network Issues (Docker)

**Error:**
```
could not translate host name "postgres" to address
```

**Solution:**
```bash
# Ensure services are on same network
docker network ls
docker network inspect multi-platform-scheduler_default

# Recreate network
docker-compose down
docker-compose up -d
```

#### 4. Connection Pool Exhausted

**Error:**
```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 10 overflow 20 reached
```

**Solution:**
```bash
# Increase pool size in .env
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Restart backend
docker-compose restart backend
```

### Migration Issues

**Symptoms:**
- "Table already exists" errors
- "Column does not exist" errors
- Migration fails

**Diagnosis:**
```bash
# Check current migration version
docker-compose exec backend alembic current

# Check migration history
docker-compose exec backend alembic history
```

**Solutions:**

#### Reset Database (Development Only)

```bash
# WARNING: This deletes all data
docker-compose down -v
docker-compose up -d postgres
docker-compose exec backend alembic upgrade head
```

#### Fix Migration Conflicts

```bash
# Stamp database to specific revision
docker-compose exec backend alembic stamp head

# Or downgrade and re-upgrade
docker-compose exec backend alembic downgrade -1
docker-compose exec backend alembic upgrade head
```

---

## Redis/Celery Issues

### Celery workers not processing tasks

**Symptoms:**
- Tasks stuck in "pending" status
- No worker logs
- Posts not being published

**Diagnosis:**
```bash
# Check worker status
docker-compose logs worker

# Check Redis connection
docker-compose exec backend python -c "import redis; r = redis.from_url('redis://redis:6379/0'); print(r.ping())"

# Inspect Celery
docker-compose exec worker celery -A src.celery_app inspect active
docker-compose exec worker celery -A src.celery_app inspect stats
```

**Common Causes:**

#### 1. Redis Not Running

**Solution:**
```bash
# Check Redis status
docker-compose ps redis

# Start Redis
docker-compose up -d redis

# Test connection
docker-compose exec redis redis-cli ping
```

#### 2. Worker Not Started

**Solution:**
```bash
# Check if worker container is running
docker-compose ps worker

# Start worker
docker-compose up -d worker

# Check logs for errors
docker-compose logs worker --tail=100
```

#### 3. Task Routing Issues

**Error:**
```
celery.exceptions.NotRegistered: 'src.tasks.post_video_job'
```

**Solution:**
```bash
# Ensure tasks are imported in celery_app.py
# Restart worker
docker-compose restart worker
```

#### 4. Memory Issues

**Error:**
```
MemoryError: Unable to allocate array
```

**Solution:**
```bash
# Increase worker memory in docker-compose.yml
services:
  worker:
    mem_limit: 2g

# Or reduce concurrency
CELERY_WORKER_CONCURRENCY=2
```

### Tasks Failing Silently

**Diagnosis:**
```bash
# Check task results
docker-compose exec backend python << EOF
from src.celery_app import celery_app
from celery.result import AsyncResult

result = AsyncResult('<task-id>', app=celery_app)
print(f"Status: {result.status}")
print(f"Result: {result.result}")
print(f"Traceback: {result.traceback}")
EOF
```

**Solution:**
- Check worker logs for exceptions
- Verify task arguments are serializable
- Ensure all dependencies are installed in worker container

---

## Authentication Problems

### Cannot login

**Symptoms:**
- "Invalid credentials" error
- Token errors
- 401 Unauthorized

**Diagnosis:**
```bash
# Test login directly
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

**Common Causes:**

#### 1. User Doesn't Exist

**Solution:**
```bash
# Register user first
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Password123!"}'

# Or check database
docker-compose exec postgres psql -U scheduler_user -d scheduler_db -c "SELECT email FROM users;"
```

#### 2. Wrong Password

**Solution:**
- Verify password meets requirements (8+ chars, uppercase, lowercase, number)
- Reset password if needed (implement password reset endpoint)

#### 3. JWT Token Issues

**Error:**
```
JWTError: Signature verification failed
```

**Solution:**
```bash
# Ensure JWT_SECRET_KEY is consistent
grep JWT_SECRET_KEY backend/.env

# Generate new secret if needed
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Update .env and restart
docker-compose restart backend
```

#### 4. Token Expired

**Error:**
```
{"detail":"Token has expired"}
```

**Solution:**
- Use refresh token to get new access token
- Implement automatic token refresh in frontend

```typescript
// Frontend token refresh
async function refreshToken() {
  const refreshToken = localStorage.getItem('refresh_token');
  const response = await fetch(`${API_URL}/api/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken })
  });
  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);
}
```

### Platform OAuth Fails

**Symptoms:**
- Redirect loop
- "Invalid redirect URI" error
- "Invalid client" error

**Diagnosis:**
```bash
# Check OAuth configuration
grep TIKTOK_REDIRECT_URI backend/.env

# Test OAuth initiation
curl http://localhost:8000/api/auth/platforms/tiktok/authorize
```

**Common Causes:**

#### 1. Redirect URI Mismatch

**Error:**
```
{"error":"redirect_uri_mismatch"}
```

**Solution:**
1. Check redirect URI in .env matches platform developer console
2. Ensure protocol (http/https) matches
3. No trailing slashes
4. Update platform developer console if needed

```bash
# Correct format
TIKTOK_REDIRECT_URI=https://yourdomain.com/api/auth/platforms/tiktok/callback
```

#### 2. Invalid Client Credentials

**Error:**
```
{"error":"invalid_client"}
```

**Solution:**
```bash
# Verify credentials in platform developer console
# Regenerate if needed
# Update .env
TIKTOK_CLIENT_KEY=<new-key>
TIKTOK_CLIENT_SECRET=<new-secret>

# Restart backend
docker-compose restart backend
```

#### 3. CORS Issues

**Error in browser console:**
```
Access to fetch at 'https://api.tiktok.com/...' has been blocked by CORS policy
```

**Solution:**
```bash
# Ensure CORS_ORIGINS includes frontend URL
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# Restart backend
docker-compose restart backend
```

---

## Platform API Issues

### TikTok API Errors

#### Rate Limit Exceeded

**Error:**
```
{"error":"rate_limit_exceeded","retry_after":3600}
```

**Solution:**
- Wait for retry_after seconds
- Implement exponential backoff
- Check rate limits in TikTok developer console
- Consider upgrading API tier

#### Video Upload Fails

**Error:**
```
{"error":"video_too_large"}
```

**Solution:**
```bash
# Check video size
ls -lh /path/to/video.mp4

# TikTok limits:
# - Max size: 287.6 MB
# - Max duration: 10 minutes
# - Formats: MP4, MOV, MPEG, AVI, WebM

# Compress video if needed
ffmpeg -i input.mp4 -c:v libx264 -crf 23 -c:a aac -b:a 128k output.mp4
```

### YouTube API Errors

#### Quota Exceeded

**Error:**
```
{"error":{"code":403,"message":"The request cannot be completed because you have exceeded your quota."}}
```

**Solution:**
- YouTube API has daily quota limits
- Request quota increase in Google Cloud Console
- Implement quota monitoring
- Schedule uploads during off-peak hours

#### Invalid Video Category

**Error:**
```
{"error":"invalid_video_category"}
```

**Solution:**
```python
# Use valid YouTube category IDs
# 22 = People & Blogs
# 23 = Comedy
# 24 = Entertainment
# 25 = News & Politics
# 26 = Howto & Style

# Update post metadata
{
  "category_id": "24",  # Entertainment
  "privacy_status": "public"
}
```

### Instagram API Errors

#### Not a Business Account

**Error:**
```
{"error":"account_not_business"}
```

**Solution:**
1. Convert Instagram account to Business or Creator account
2. Link to Facebook Page
3. Re-authenticate in app

#### Video Format Not Supported

**Error:**
```
{"error":"invalid_media_type"}
```

**Solution:**
```bash
# Instagram Reels requirements:
# - Format: MP4
# - Codec: H.264
# - Aspect ratio: 9:16 (vertical)
# - Duration: 3-90 seconds
# - Max size: 100 MB

# Convert video
ffmpeg -i input.mp4 \
  -c:v libx264 \
  -profile:v main \
  -level 3.1 \
  -preset medium \
  -crf 23 \
  -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2" \
  -c:a aac \
  -b:a 128k \
  -movflags +faststart \
  output.mp4
```

---

## Video Upload Problems

### Upload to S3 Fails

**Symptoms:**
- "Access Denied" errors
- Timeout errors
- Upload progress stuck

**Diagnosis:**
```bash
# Test S3 access
aws s3 ls s3://your-bucket-name

# Test upload
echo "test" > test.txt
aws s3 cp test.txt s3://your-bucket-name/test.txt
```

**Common Causes:**

#### 1. Invalid AWS Credentials

**Error:**
```
botocore.exceptions.NoCredentialsError: Unable to locate credentials
```

**Solution:**
```bash
# Verify credentials in .env
grep AWS_ACCESS_KEY_ID backend/.env
grep AWS_SECRET_ACCESS_KEY backend/.env

# Test credentials
aws sts get-caller-identity

# Update if invalid
```

#### 2. Insufficient S3 Permissions

**Error:**
```
botocore.exceptions.ClientError: An error occurred (AccessDenied) when calling the PutObject operation
```

**Solution:**
```json
// Add IAM policy
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
        "arn:aws:s3:::your-bucket-name",
        "arn:aws:s3:::your-bucket-name/*"
      ]
    }
  ]
}
```

#### 3. File Too Large

**Error:**
```
{"detail":"File size exceeds maximum allowed size"}
```

**Solution:**
```bash
# Check file size limit in config
grep MAX_UPLOAD_SIZE backend/src/config.py

# Increase if needed (in bytes)
MAX_UPLOAD_SIZE=524288000  # 500 MB

# Or compress video before upload
```

### Video Conversion Fails

**Symptoms:**
- Conversion task stuck
- FFmpeg errors
- Output video corrupted

**Diagnosis:**
```bash
# Check worker logs
docker-compose logs worker | grep -i ffmpeg

# Test FFmpeg manually
docker-compose exec worker ffmpeg -version
```

**Common Causes:**

#### 1. FFmpeg Not Installed

**Solution:**
```dockerfile
# Ensure Dockerfile includes FFmpeg
RUN apt-get update && apt-get install -y ffmpeg
```

#### 2. Invalid Input Video

**Error:**
```
[error] Invalid data found when processing input
```

**Solution:**
```bash
# Validate video file
ffmpeg -v error -i input.mp4 -f null -

# Re-encode if corrupted
ffmpeg -i input.mp4 -c copy output.mp4
```

#### 3. Insufficient Memory

**Error:**
```
MemoryError during video conversion
```

**Solution:**
```yaml
# Increase worker memory in docker-compose.yml
services:
  worker:
    mem_limit: 4g
    memswap_limit: 4g
```

---

## Posting Failures

### Post Stuck in "Pending" Status

**Diagnosis:**
```bash
# Check Celery queue
docker-compose exec worker celery -A src.celery_app inspect active

# Check task status in database
docker-compose exec postgres psql -U scheduler_user -d scheduler_db \
  -c "SELECT id, platform, status, error_message FROM posts WHERE status='pending' ORDER BY created_at DESC LIMIT 10;"
```

**Solutions:**

1. **Restart worker:**
```bash
docker-compose restart worker
```

2. **Manually retry post:**
```bash
curl -X POST http://localhost:8000/api/posts/{post_id}/retry
```

3. **Check platform authentication:**
```bash
# Verify platform tokens are valid
docker-compose exec postgres psql -U scheduler_user -d scheduler_db \
  -c "SELECT platform, is_active, token_expires_at FROM platform_auth WHERE user_id='<user-id>';"
```

### Post Fails with "Authentication Required"

**Error:**
```
{"error":"platform_auth_required","platform":"tiktok"}
```

**Solution:**
1. Re-authenticate with platform
2. Check token expiration
3. Verify refresh token is valid

```bash
# Force token refresh
curl -X POST http://localhost:8000/api/auth/platforms/tiktok/refresh \
  -H "Authorization: Bearer <your-jwt-token>"
```

### Scheduled Posts Not Executing

**Diagnosis:**
```bash
# Check Celery beat is running
docker-compose ps | grep beat

# Check scheduled tasks
docker-compose exec worker celery -A src.celery_app inspect scheduled
```

**Solutions:**

1. **Start Celery beat:**
```bash
# Add to docker-compose.yml if missing
services:
  beat:
    build: ./backend
    command: celery -A src.celery_app beat --loglevel=info
    depends_on:
      - redis
```

2. **Check schedule configuration:**
```python
# In src/celery_app.py
celery_app.conf.beat_schedule = {
    'process-scheduled-posts': {
        'task': 'src.tasks.process_scheduled_posts',
        'schedule': 60.0,  # Every 60 seconds
    },
}
```

---

## Performance Issues

### Slow API Response Times

**Diagnosis:**
```bash
# Check response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/api/videos

# curl-format.txt:
time_namelookup:  %{time_namelookup}\n
time_connect:  %{time_connect}\n
time_starttransfer:  %{time_starttransfer}\n
time_total:  %{time_total}\n
```

**Solutions:**

#### 1. Database Query Optimization

```bash
# Enable query logging
LOG_LEVEL=DEBUG

# Check slow queries
docker-compose exec postgres psql -U scheduler_user -d scheduler_db \
  -c "SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
```

Add indexes:
```sql
CREATE INDEX idx_posts_user_id ON posts(user_id);
CREATE INDEX idx_posts_status ON posts(status);
CREATE INDEX idx_videos_user_id ON videos(user_id);
```

#### 2. Connection Pool Tuning

```bash
# Increase pool size
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Restart backend
docker-compose restart backend
```

#### 3. Add Caching

```python
# Install redis cache
pip install fastapi-cache2

# Add to endpoints
from fastapi_cache.decorator import cache

@router.get("/videos")
@cache(expire=60)
async def get_videos():
    ...
```

### High Memory Usage

**Diagnosis:**
```bash
# Check container memory
docker stats

# Check Python memory usage
docker-compose exec backend python -c "
import psutil
process = psutil.Process()
print(f'Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

**Solutions:**

1. **Limit worker concurrency:**
```bash
CELERY_WORKER_CONCURRENCY=2
```

2. **Process videos in chunks:**
```python
# Instead of loading entire video in memory
with open(video_path, 'rb') as f:
    while chunk := f.read(8192):
        process_chunk(chunk)
```

3. **Increase container memory:**
```yaml
services:
  backend:
    mem_limit: 2g
```

---

## Frontend Issues

### API Requests Failing

**Error in browser console:**
```
Failed to fetch
TypeError: NetworkError when attempting to fetch resource
```

**Solutions:**

#### 1. CORS Issues

```bash
# Check CORS configuration in backend
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# Restart backend
docker-compose restart backend
```

#### 2. Wrong API URL

```bash
# Check frontend .env.local
cat frontend/.env.local

# Should match backend URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

#### 3. Backend Not Running

```bash
# Check backend status
curl http://localhost:8000/health

# Start if not running
docker-compose up -d backend
```

### Authentication Not Persisting

**Symptoms:**
- User logged out on page refresh
- Token not being sent with requests

**Solutions:**

1. **Check localStorage:**
```javascript
// In browser console
console.log(localStorage.getItem('access_token'));
```

2. **Verify token in requests:**
```typescript
// Ensure Authorization header is set
fetch(`${API_URL}/api/videos`, {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
  }
});
```

3. **Implement token refresh:**
```typescript
// Add interceptor to refresh expired tokens
axios.interceptors.response.use(
  response => response,
  async error => {
    if (error.response?.status === 401) {
      await refreshToken();
      return axios.request(error.config);
    }
    return Promise.reject(error);
  }
);
```

---

## Docker Issues

### Container Keeps Restarting

**Diagnosis:**
```bash
# Check container status
docker-compose ps

# Check logs
docker-compose logs <service-name>

# Check exit code
docker inspect <container-id> --format='{{.State.ExitCode}}'
```

**Common Exit Codes:**
- 0: Normal exit
- 1: Application error
- 137: Out of memory (OOM killed)
- 139: Segmentation fault

**Solutions:**

1. **Fix application errors** (exit code 1)
2. **Increase memory** (exit code 137)
3. **Check dependencies** (segfault)

### Cannot Connect Between Containers

**Error:**
```
could not translate host name "postgres" to address
```

**Solution:**
```bash
# Check network
docker network ls
docker network inspect multi-platform-scheduler_default

# Ensure services use correct hostnames
# In backend .env:
DATABASE_URL=postgresql://user:pass@postgres:5432/db
REDIS_URL=redis://redis:6379/0

# Restart services
docker-compose down
docker-compose up -d
```

### Volume Permission Issues

**Error:**
```
PermissionError: [Errno 13] Permission denied
```

**Solution:**
```bash
# Fix permissions
sudo chown -R $USER:$USER ./data

# Or run container as current user
docker-compose run --user $(id -u):$(id -g) backend bash
```

---

## Common Error Messages

### "Database is locked"

**Cause:** SQLite being used instead of PostgreSQL (development only)

**Solution:**
```bash
# Switch to PostgreSQL
DATABASE_URL=postgresql://user:pass@localhost:5432/db
```

### "Connection pool exhausted"

**Cause:** Too many concurrent database connections

**Solution:**
```bash
# Increase pool size
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
```

### "Task timeout"

**Cause:** Task taking longer than time limit

**Solution:**
```bash
# Increase task time limit
CELERY_TASK_TIME_LIMIT=7200  # 2 hours
CELERY_TASK_SOFT_TIME_LIMIT=6000  # 100 minutes
```

### "Signature verification failed"

**Cause:** JWT secret key mismatch

**Solution:**
```bash
# Ensure JWT_SECRET_KEY is consistent across all instances
# Restart all services after changing
docker-compose restart
```

---

## Getting Help

If you're still experiencing issues:

1. **Check logs thoroughly:**
```bash
docker-compose logs --tail=1000 > logs.txt
```

2. **Enable debug mode:**
```bash
DEBUG=true
LOG_LEVEL=DEBUG
```

3. **Collect system information:**
```bash
docker version
docker-compose version
python --version
node --version
```

4. **Search existing issues:**
- Check GitHub issues
- Search error messages online

5. **Create detailed bug report:**
- Steps to reproduce
- Expected vs actual behavior
- Logs and error messages
- Environment details
- Screenshots if applicable

---

## Preventive Measures

### Regular Maintenance

```bash
# Clean up Docker
docker system prune -a

# Update dependencies
pip install --upgrade -r requirements.txt
npm update

# Backup database
docker-compose exec postgres pg_dump -U scheduler_user scheduler_db > backup.sql

# Monitor disk space
df -h

# Monitor logs
docker-compose logs --tail=100 -f
```

### Health Checks

```bash
# Create monitoring script
cat > health-check.sh << 'EOF'
#!/bin/bash
echo "Checking backend..."
curl -f http://localhost:8000/health || echo "Backend unhealthy"

echo "Checking frontend..."
curl -f http://localhost:3000 || echo "Frontend unhealthy"

echo "Checking database..."
docker-compose exec -T postgres pg_isready || echo "Database unhealthy"

echo "Checking Redis..."
docker-compose exec -T redis redis-cli ping || echo "Redis unhealthy"
EOF

chmod +x health-check.sh
./health-check.sh
```

### Automated Alerts

Set up monitoring with tools like:
- Sentry for error tracking
- Prometheus + Grafana for metrics
- CloudWatch for AWS deployments
- UptimeRobot for uptime monitoring

---

For additional support, refer to:
- [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
- [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md)
- Platform-specific documentation (TikTok, YouTube, Instagram, Facebook)
