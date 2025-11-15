# Get Started with Multi-Platform Video Scheduler

## 🎯 Choose Your Path

### Path 1: Automated Setup (Recommended) ⚡
**Time: 5 minutes**

```bash
cd multi-platform-scheduler

# Run the setup script
./setup.sh

# Start all services
./start.sh

# Check status
./status.sh
```

That's it! Your app is running at:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000

### Path 2: Manual Setup 🔧
**Time: 10 minutes**

Follow the detailed steps in `QUICKSTART.md`

---

## ✅ Verify Everything Works

### Quick Test (2 minutes)

1. **Open Frontend**: http://localhost:3000
   - You should see the login/register page

2. **Check Backend**: http://localhost:8000
   - You should see: `{"message": "Multi-Platform Video Scheduler API", ...}`

3. **View API Docs**: http://localhost:8000/docs
   - Interactive API documentation

4. **Register a Test User**:
   - Go to http://localhost:3000/register
   - Email: `test@example.com`
   - Password: `Password123!`
   - Should redirect to dashboard

5. **Check Status**:
   ```bash
   ./status.sh
   ```
   All services should show green checkmarks ✓

---

## 🎮 What You Can Test Now

With the basic setup, you can test:

✅ **User Authentication**
- Register new users
- Login/logout
- JWT token management
- Protected routes

✅ **Frontend Navigation**
- Dashboard
- Platform connections page
- Video library page
- Post creation page
- Schedule management

✅ **API Endpoints**
- All authentication endpoints
- User management
- Database operations

✅ **Error Handling**
- Form validation
- API error responses
- Network error handling

---

## ⏳ What Needs Configuration

To test the full feature set, you'll need to configure:

### 1. Platform OAuth (Required for posting)
- TikTok Developer App
- YouTube API credentials
- Instagram Graph API
- Facebook Graph API

See `PLATFORM_OAUTH_SETUP.md` for detailed instructions.

### 2. AWS S3 (Required for video uploads)
- Create S3 bucket
- Configure IAM credentials
- Update `backend/.env`

### 3. Email Service (Optional - for notifications)
- SMTP server or SendGrid
- Update email settings in `backend/.env`

---

## 🧪 Testing Without Full Configuration

You can still test most features without platform APIs:

### Test Authentication Flow
```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Password123!"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Password123!"}'
```

### Test Database
```bash
# Connect to PostgreSQL
docker exec -it multi-platform-scheduler-postgres-1 psql -U postgres -d video_scheduler

# List users
SELECT email, created_at FROM users;

# Exit
\q
```

### Test Frontend UI
- Navigate through all pages
- Test form validation
- Check responsive design (resize browser)
- Test error messages

---

## 📊 Monitoring Your App

### View Logs

```bash
# Backend logs
tail -f logs/backend.log

# Frontend logs
tail -f logs/frontend.log

# Celery logs
tail -f logs/celery.log

# All logs
tail -f logs/*.log
```

### Check Status

```bash
# Quick status check
./status.sh

# Detailed Docker status
docker-compose ps

# Check specific service
docker-compose logs postgres
docker-compose logs redis
```

### Database Queries

```bash
# Connect to database
docker exec -it multi-platform-scheduler-postgres-1 psql -U postgres -d video_scheduler

# Useful queries
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM videos;
SELECT COUNT(*) FROM posts;
SELECT platform, COUNT(*) FROM posts GROUP BY platform;
```

---

## 🛠️ Common Commands

### Start/Stop Services

```bash
# Start everything
./start.sh

# Stop everything
./stop.sh

# Check status
./status.sh

# Restart a service
docker-compose restart postgres
docker-compose restart redis
```

### Database Management

```bash
cd backend

# Run migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Reset database (WARNING: deletes all data)
alembic downgrade base
alembic upgrade head
```

### Clear Data

```bash
# Clear all data but keep schema
docker exec -it multi-platform-scheduler-postgres-1 psql -U postgres -d video_scheduler -c "TRUNCATE users CASCADE;"

# Reset Redis
docker exec -it multi-platform-scheduler-redis-1 redis-cli FLUSHALL
```

---

## 🐛 Troubleshooting

### Services Won't Start

```bash
# Check if ports are in use
lsof -ti:8000  # Backend
lsof -ti:3000  # Frontend
lsof -ti:5432  # PostgreSQL
lsof -ti:6379  # Redis

# Kill processes if needed
lsof -ti:8000 | xargs kill -9
```

### Database Connection Errors

```bash
# Restart PostgreSQL
docker-compose restart postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Verify connection
docker exec -it multi-platform-scheduler-postgres-1 psql -U postgres -c "SELECT 1;"
```

### Frontend Build Errors

```bash
cd frontend

# Clear cache and reinstall
rm -rf node_modules .next
npm install
npm run dev
```

### Backend Import Errors

```bash
cd backend

# Reinstall dependencies
pip install -r requirements.txt

# Check Python version (should be 3.11+)
python3 --version
```

---

## 📚 Next Steps

### 1. Run Smoke Tests (5 minutes)
Follow the tests in `QUICK_TEST_GUIDE.md`

### 2. Configure Platform OAuth (30 minutes)
See `PLATFORM_OAUTH_SETUP.md` (to be created)

### 3. Set Up AWS S3 (15 minutes)
See `AWS_SETUP.md` (to be created)

### 4. Run Full Manual Tests (1-2 hours)
Follow `MANUAL_TESTING_CHECKLIST.md`

### 5. Deploy to Staging
Follow `DEPLOYMENT_GUIDE.md`

---

## 🎓 Learning Resources

### Understanding the Architecture
- `docs/ARCHITECTURE.md` - System design
- `backend/src/` - Backend code structure
- `frontend/` - Frontend code structure

### API Documentation
- http://localhost:8000/docs - Interactive API docs
- http://localhost:8000/redoc - Alternative API docs

### Database Schema
- `backend/src/models/database_models.py` - All models
- `backend/alembic/versions/` - Migration history

---

## 💡 Tips for Testing

1. **Start Simple**: Test authentication first, then add features
2. **Use API Docs**: http://localhost:8000/docs for testing endpoints
3. **Check Logs**: Always check logs when something doesn't work
4. **Test Mobile**: Resize browser to test responsive design
5. **Use Incognito**: Test auth flows in incognito mode

---

## 🆘 Need Help?

1. Check `TROUBLESHOOTING.md` for common issues
2. Review logs in `logs/` directory
3. Check `./status.sh` for service status
4. Verify environment variables in `.env` files
5. Ensure all dependencies are installed

---

## ✨ You're All Set!

Your Multi-Platform Video Scheduler is now running locally. Start with the smoke tests, then gradually add platform configurations as needed.

**Happy Testing! 🎉**
