# Setup Without Docker

If you don't have Docker installed, you can still run the Multi-Platform Video Scheduler using local PostgreSQL and Redis installations.

## 🚀 Quick Setup (macOS with Homebrew)

### Step 1: Install PostgreSQL and Redis (5 minutes)

```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install PostgreSQL and Redis
brew install postgresql@14 redis

# Start services
brew services start postgresql@14
brew services start redis

# Verify they're running
brew services list
```

### Step 2: Create Database (2 minutes)

```bash
# Create database
createdb video_scheduler

# Verify it was created
psql -l | grep video_scheduler
```

### Step 3: Update Environment Files (2 minutes)

```bash
cd multi-platform-scheduler

# Copy environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Edit `backend/.env` and update these lines:

```bash
# Change from Docker URLs to local URLs
DATABASE_URL=postgresql+asyncpg://$(whoami)@localhost:5432/video_scheduler
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

Generate secure keys:

```bash
# Generate SECRET_KEY
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"

# Generate JWT_SECRET_KEY
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"

# Generate ENCRYPTION_KEY (must be exactly 32 characters)
python3 -c "import secrets; print('ENCRYPTION_KEY=' + secrets.token_urlsafe(32)[:32])"
```

Copy these values into your `backend/.env` file.

### Step 4: Set Up Backend (3 minutes)

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

cd ..
```

### Step 5: Set Up Frontend (2 minutes)

```bash
cd frontend

# Install dependencies
npm install

cd ..
```

### Step 6: Start Services (1 minute)

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

**Terminal 3 - Celery Worker (Optional):**
```bash
cd backend
source venv/bin/activate
celery -A src.celery_app worker --loglevel=info
```

### Step 7: Verify Setup (1 minute)

Open your browser:

1. **Frontend**: http://localhost:3000
2. **Backend**: http://localhost:8000
3. **API Docs**: http://localhost:8000/docs

Try registering a user at http://localhost:3000/register

---

## ✅ Quick Test

```bash
# Test PostgreSQL connection
psql video_scheduler -c "SELECT 1;"

# Test Redis connection
redis-cli ping
# Should return: PONG

# Test backend health
curl http://localhost:8000/health

# Check database has tables
psql video_scheduler -c "\dt"
```

---

## 🛠️ Managing Services

### Start Services
```bash
# PostgreSQL
brew services start postgresql@14

# Redis
brew services start redis
```

### Stop Services
```bash
# PostgreSQL
brew services stop postgresql@14

# Redis
brew services stop redis
```

### Check Status
```bash
brew services list
```

### View Logs
```bash
# PostgreSQL logs
tail -f /opt/homebrew/var/log/postgresql@14.log

# Redis logs
tail -f /opt/homebrew/var/log/redis.log
```

---

## 🐛 Troubleshooting

### PostgreSQL Connection Issues

```bash
# Check if PostgreSQL is running
brew services list | grep postgresql

# Restart PostgreSQL
brew services restart postgresql@14

# Check PostgreSQL logs
tail -f /opt/homebrew/var/log/postgresql@14.log

# Test connection
psql -d video_scheduler -c "SELECT version();"
```

### Redis Connection Issues

```bash
# Check if Redis is running
brew services list | grep redis

# Restart Redis
brew services restart redis

# Test connection
redis-cli ping
```

### Database Migration Issues

```bash
cd backend
source venv/bin/activate

# Check current migration version
alembic current

# Reset database (WARNING: deletes all data)
alembic downgrade base
alembic upgrade head
```

### Port Already in Use

```bash
# Find process using port 8000
lsof -ti:8000

# Kill it
lsof -ti:8000 | xargs kill -9

# Same for port 3000
lsof -ti:3000 | xargs kill -9
```

---

## 📊 Database Management

### Connect to Database
```bash
psql video_scheduler
```

### Useful Commands
```sql
-- List all tables
\dt

-- List all users
SELECT email, created_at FROM users;

-- Count records
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM videos;
SELECT COUNT(*) FROM posts;

-- Exit
\q
```

### Backup Database
```bash
pg_dump video_scheduler > backup.sql
```

### Restore Database
```bash
psql video_scheduler < backup.sql
```

### Reset Database
```bash
# Drop and recreate
dropdb video_scheduler
createdb video_scheduler

# Run migrations
cd backend
source venv/bin/activate
alembic upgrade head
```

---

## 🔄 Alternative: Install Docker

If you prefer to use Docker (recommended for production-like environment):

### Install Docker Desktop for Mac

1. Download from: https://www.docker.com/products/docker-desktop
2. Install and start Docker Desktop
3. Verify installation:
   ```bash
   docker --version
   docker compose version
   ```
4. Run the original setup:
   ```bash
   ./setup.sh
   ```

---

## 📚 Next Steps

Once everything is running:

1. **Test Authentication**: Register and login at http://localhost:3000
2. **Check API Docs**: Visit http://localhost:8000/docs
3. **Run Smoke Tests**: Follow `QUICK_TEST_GUIDE.md`
4. **Full Testing**: Follow `MANUAL_TESTING_CHECKLIST.md`

---

## 💡 Tips

1. **Keep services running**: PostgreSQL and Redis should always be running when testing
2. **Use separate terminals**: One for backend, one for frontend, one for Celery
3. **Check logs**: If something fails, check the terminal output
4. **Restart services**: If things get stuck, restart PostgreSQL and Redis

---

## 🆘 Still Having Issues?

1. Check `TROUBLESHOOTING.md` for common problems
2. Verify PostgreSQL and Redis are running: `brew services list`
3. Check database exists: `psql -l | grep video_scheduler`
4. Test connections manually (see Quick Test section above)
5. Check environment variables in `backend/.env`

---

**You're all set! Start testing with the smoke tests in `QUICK_TEST_GUIDE.md`** 🎉
