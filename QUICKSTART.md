# Quick Start Guide

Get your Multi-Platform Video Scheduler up and running in minutes!

## 🚀 Fast Setup (5 Minutes)

### Step 1: Copy Environment Files (30 seconds)

```bash
cd multi-platform-scheduler

# Backend
cp backend/.env.example backend/.env

# Frontend
cp frontend/.env.example frontend/.env
```

### Step 2: Generate Secret Keys (30 seconds)

Run these commands to generate secure keys:

```bash
# Generate SECRET_KEY (for backend/.env)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate JWT_SECRET_KEY (for backend/.env)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate ENCRYPTION_KEY (for backend/.env - must be 32 bytes)
python3 -c "import secrets; print(secrets.token_urlsafe(32)[:32])"
```

Copy these values into your `backend/.env` file.

### Step 3: Start Services (2 minutes)

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Wait for services to be ready (about 10 seconds)
sleep 10

# Check services are running
docker-compose ps
```

### Step 4: Set Up Database (1 minute)

```bash
cd backend

# Install dependencies (if not already done)
pip install -r requirements.txt

# Run migrations
alembic upgrade head

cd ..
```

### Step 5: Start Application (1 minute)

**Terminal 1 - Backend:**
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm install  # First time only
npm run dev
```

**Terminal 3 - Celery Worker (Optional for now):**
```bash
cd backend
celery -A src.celery_app worker --loglevel=info
```

### Step 6: Verify Setup (30 seconds)

Open your browser:

1. **Backend API**: http://localhost:8000
   - Should see: `{"message": "Multi-Platform Video Scheduler API", ...}`

2. **Frontend**: http://localhost:3000
   - Should see the login/register page

3. **API Docs**: http://localhost:8000/docs
   - Should see FastAPI interactive documentation

---

## ✅ Quick Smoke Test (2 Minutes)

### Test 1: Register & Login
1. Go to http://localhost:3000/register
2. Register with: `test@example.com` / `Password123!`
3. Should redirect to dashboard
4. Logout and login again
5. ✅ If successful, authentication works!

### Test 2: Check Database
```bash
docker exec -it multi-platform-scheduler-postgres-1 psql -U postgres -d video_scheduler -c "SELECT email FROM users;"
```
You should see your test user.

### Test 3: API Health Check
```bash
curl http://localhost:8000/health
```
Should return: `{"status": "healthy", ...}`

---

## 🎯 What's Working Now

With this minimal setup, you can test:

✅ User registration and login  
✅ JWT authentication  
✅ Database operations  
✅ Frontend-backend communication  
✅ Protected routes  

## ⏳ What Needs Configuration

To test full features, you'll need:

❌ **Platform OAuth** (TikTok, YouTube, Instagram, Facebook)  
❌ **AWS S3** (for video uploads)  
❌ **Email Service** (for notifications)  
❌ **Celery Beat** (for scheduled posts)  

---

## 🔧 Minimal Configuration for Testing

If you want to test without platform APIs, you can:

### Option 1: Use Local File Storage (Instead of S3)

Edit `backend/src/config.py` to add a local storage option, or just skip video upload tests for now.

### Option 2: Mock Platform Connections

For testing the UI without real OAuth, you can manually insert platform auth records into the database.

### Option 3: Test Core Features Only

Focus on testing:
- Authentication
- Database operations
- UI navigation
- Form validation
- Error handling

---

## 🐛 Troubleshooting

### "Connection refused" errors
```bash
# Check if services are running
docker-compose ps

# Restart services
docker-compose restart postgres redis
```

### "Module not found" errors
```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### Database migration errors
```bash
cd backend
# Reset database (WARNING: deletes all data)
alembic downgrade base
alembic upgrade head
```

### Port already in use
```bash
# Find process using port 8000
lsof -ti:8000 | xargs kill -9

# Find process using port 3000
lsof -ti:3000 | xargs kill -9
```

---

## 📚 Next Steps

Once basic setup works:

1. **Configure Platform OAuth** (see `PLATFORM_OAUTH_SETUP.md`)
2. **Set up AWS S3** (see `AWS_SETUP.md`)
3. **Run Full Tests** (see `QUICK_TEST_GUIDE.md`)
4. **Deploy to Staging** (see `DEPLOYMENT_GUIDE.md`)

---

## 🎉 You're Ready!

Your development environment is now running. Start testing with the smoke tests above, then move to the comprehensive testing checklist in `MANUAL_TESTING_CHECKLIST.md`.

**Need help?** Check `TROUBLESHOOTING.md` for common issues and solutions.
