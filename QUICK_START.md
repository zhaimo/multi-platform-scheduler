# Quick Start Guide

## Current Issue
You're getting "Registration failed" because the PostgreSQL database isn't running.

## Solution: Start Docker and All Services

### Step 1: Start Docker Desktop
1. **Open Docker Desktop** application on your Mac
2. **Wait** for the Docker icon in your menu bar to show it's running (steady whale icon)
3. This usually takes 30-60 seconds

### Step 2: Verify Docker is Running
```bash
docker ps
```

You should see output (even if empty). If you see "Cannot connect to the Docker daemon", Docker isn't running yet.

### Step 3: Start All Services
```bash
cd multi-platform-scheduler
./start.sh
```

This will start:
- ✅ PostgreSQL database (port 5432)
- ✅ Redis (port 6379)
- ✅ Backend API (port 8000)
- ✅ Frontend (port 3000)
- ✅ Celery worker

### Step 4: Verify Services
```bash
# Check Docker containers
docker ps

# Should show:
# - video-scheduler-postgres
# - video-scheduler-redis

# Check backend
curl http://localhost:8000/health

# Should return: {"status":"healthy",...}
```

### Step 5: Register a User
1. Go to http://localhost:3000/register
2. Enter:
   - **Email**: your@email.com
   - **Password**: TestPass123 (must have uppercase, lowercase, and numbers)
3. Click "Register"
4. You should be redirected to the dashboard

### Step 6: Test Login
1. Go to http://localhost:3000/login
2. Enter your credentials
3. You should be logged in successfully

## Troubleshooting

### "Cannot connect to Docker daemon"
**Problem**: Docker Desktop isn't running
**Solution**: 
1. Open Docker Desktop app
2. Wait for it to fully start
3. Try again

### "Port already in use"
**Problem**: Services are already running
**Solution**:
```bash
./stop.sh
./start.sh
```

### "Connection refused" in logs
**Problem**: Database isn't running
**Solution**:
```bash
# Check if Docker containers are running
docker ps

# If not, start them
docker-compose up -d postgres redis

# Wait 5 seconds for database to initialize
sleep 5

# Restart backend
./stop.sh
./start.sh
```

### Still Having Issues?
Check the logs:
```bash
# Backend logs (look for database connection errors)
tail -f logs/backend.log

# Docker logs
docker logs video-scheduler-postgres
docker logs video-scheduler-redis
```

## Quick Test Commands

Test registration via API:
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123"
  }'
```

Expected response:
```json
{
  "id": "...",
  "email": "test@example.com",
  "created_at": "..."
}
```

Test login via API:
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123"
  }'
```

Expected response:
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

## What's Next?

Once logged in, you can:
1. Connect social media platforms (TikTok, YouTube, Twitter, Instagram, Facebook)
2. Upload videos
3. Schedule posts
4. Manage your content

See `PLATFORM_SETUP.md` for platform-specific setup instructions.
