# Login Troubleshooting Guide

## Issue: "Login failed. Please try again."

### Root Cause
The backend cannot connect to the PostgreSQL database because Docker is not running.

### Solution

#### Step 1: Start Docker Desktop
1. Open Docker Desktop application on your Mac
2. Wait for Docker to fully start (whale icon in menu bar should be steady)

#### Step 2: Start All Services
```bash
cd multi-platform-scheduler
./start.sh
```

This will start:
- PostgreSQL database
- Redis
- Backend API
- Frontend
- Celery worker

#### Step 3: Verify Services Are Running
```bash
./status.sh
```

Or manually check:
```bash
# Check Docker containers
docker ps

# Check backend
curl http://localhost:8000/health

# Check frontend
curl -I http://localhost:3000
```

### Creating a Test User

#### Option 1: Register via Frontend
1. Go to http://localhost:3000/register
2. Enter email and password
3. Password requirements:
   - At least 8 characters
   - At least one uppercase letter
   - At least one lowercase letter
   - At least one number

Example valid password: `TestPass123`

#### Option 2: Register via API
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123"
  }'
```

#### Option 3: Create User via Script
```bash
cd backend
source venv/bin/activate
python3 << EOF
import asyncio
from src.database import get_db
from src.models.database_models import User
from src.utils.auth import get_password_hash
from uuid import uuid4
from datetime import datetime

async def create_user():
    async for db in get_db():
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash=get_password_hash("TestPass123"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            notification_preferences={}
        )
        db.add(user)
        await db.commit()
        print(f"User created: {user.email}")
        break

asyncio.run(create_user())
EOF
```

### Common Issues

#### Issue: "Connection refused"
**Cause:** Database is not running
**Solution:** Start Docker and run `./start.sh`

#### Issue: "Password validation failed"
**Cause:** Password doesn't meet requirements
**Solution:** Use a password with uppercase, lowercase, and numbers (e.g., `TestPass123`)

#### Issue: "Email already exists"
**Cause:** User already registered
**Solution:** Use the login page instead, or use a different email

### Checking Logs

If issues persist, check the logs:

```bash
# Backend logs
tail -f logs/backend.log

# Frontend logs  
tail -f logs/frontend.log

# Database logs
docker logs video-scheduler-postgres
```

### Quick Test

Test the full authentication flow:

```bash
# 1. Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123"}'

# 2. Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123"}'

# Should return:
# {"access_token":"...","refresh_token":"...","token_type":"bearer"}
```

### Still Having Issues?

1. Check if all services are running: `./status.sh`
2. Restart all services: `./stop.sh && ./start.sh`
3. Check backend logs for specific errors
4. Verify database connection in logs
5. Try registering a new user first before logging in
