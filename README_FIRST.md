# ⚠️ READ THIS FIRST - Registration/Login Issues

## The Problem
You're seeing **"Registration failed. Please try again."** because the PostgreSQL database is not running.

## The Root Cause
Docker Desktop is not running on your Mac, so the database container cannot start.

## The Solution (3 Simple Steps)

### 1️⃣ Start Docker Desktop
- Open the **Docker Desktop** application on your Mac
- Wait for the whale icon in your menu bar to be steady (not animated)
- This takes about 30-60 seconds

### 2️⃣ Start All Services
```bash
cd multi-platform-scheduler
./start.sh
```

### 3️⃣ Check Everything is Running
```bash
./check-services.sh
```

You should see all green checkmarks ✓

## Now Try Again

### Register a New User
1. Go to http://localhost:3000/register
2. Email: `your@email.com`
3. Password: `TestPass123` (must have uppercase, lowercase, numbers)
4. Click Register

### Or Test via Command Line
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123"}'
```

## Still Not Working?

Run the diagnostic script:
```bash
./check-services.sh
```

This will tell you exactly what's not running and how to fix it.

## Quick Links
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Detailed Guide**: See `QUICK_START.md`
- **Troubleshooting**: See `LOGIN_TROUBLESHOOTING.md`

---

**TL;DR**: Start Docker Desktop, then run `./start.sh`, then try registering again.
