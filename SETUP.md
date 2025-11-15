# Setup Guide

This guide will help you set up the Multi-Platform Video Scheduler for development.

## Prerequisites

- Docker and Docker Compose (recommended)
- Python 3.11+ (for local backend development)
- Node.js 20+ (for local frontend development)
- PostgreSQL 15+ (if not using Docker)
- Redis (if not using Docker)

## Quick Start with Docker (Recommended)

1. **Clone the repository and navigate to the project:**
   ```bash
   cd multi-platform-scheduler
   ```

2. **Set up environment files:**
   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   ```

3. **Configure your environment variables:**
   Edit `backend/.env` and add your:
   - Secret keys (generate secure random strings)
   - AWS credentials
   - Platform API credentials (TikTok, YouTube, Instagram, Facebook)
   - Email SMTP settings (optional)

4. **Start all services:**
   ```bash
   docker-compose up -d
   ```

5. **Check service status:**
   ```bash
   docker-compose ps
   ```

6. **View logs:**
   ```bash
   docker-compose logs -f
   ```

7. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - PostgreSQL: localhost:5432
   - Redis: localhost:6379

## Local Development Setup

### Backend Setup

1. **Create a virtual environment:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start PostgreSQL and Redis:**
   ```bash
   docker-compose up -d postgres redis
   ```

5. **Run the backend:**
   ```bash
   uvicorn main:app --reload
   ```

6. **In a separate terminal, start Celery worker:**
   ```bash
   celery -A src.celery_app worker --loglevel=info
   ```

7. **In another terminal, start Celery beat:**
   ```bash
   celery -A src.celery_app beat --loglevel=info
   ```

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env if needed
   ```

4. **Run the development server:**
   ```bash
   npm run dev
   ```

## Platform API Setup

### TikTok

1. Create a TikTok Developer account at https://developers.tiktok.com/
2. Create a new app
3. Add the following scopes: `video.upload`, `user.info.basic`
4. Set redirect URI to: `http://localhost:3000/api/auth/platforms/tiktok/callback`
5. Copy Client Key and Client Secret to your `.env` file

### YouTube

1. Go to Google Cloud Console: https://console.cloud.google.com/
2. Create a new project
3. Enable YouTube Data API v3
4. Create OAuth 2.0 credentials
5. Add redirect URI: `http://localhost:3000/api/auth/platforms/youtube/callback`
6. Copy Client ID and Client Secret to your `.env` file

### Instagram

1. Create a Facebook Developer account: https://developers.facebook.com/
2. Create a new app
3. Add Instagram Graph API product
4. Configure OAuth redirect URI: `http://localhost:3000/api/auth/platforms/instagram/callback`
5. Copy App ID and App Secret to your `.env` file

### Facebook

1. Use the same Facebook Developer app from Instagram setup
2. Add Facebook Login product
3. Configure OAuth redirect URI: `http://localhost:3000/api/auth/platforms/facebook/callback`
4. Copy App ID and App Secret to your `.env` file

## AWS S3 Setup

1. Create an AWS account if you don't have one
2. Create an S3 bucket for video storage
3. Create an IAM user with S3 access
4. Generate access keys
5. Add credentials to your `.env` file

## Database Migrations

Once the database is running, you'll need to run migrations (to be implemented in task 2):

```bash
cd backend
alembic upgrade head
```

## Testing

### Backend Tests

```bash
cd backend
pytest
```

### Frontend Tests

```bash
cd frontend
npm test
```

## Troubleshooting

### Port Already in Use

If you get port conflicts, you can change the ports in `docker-compose.yml` or stop the conflicting services.

### Database Connection Issues

Make sure PostgreSQL is running and the connection string in `.env` is correct.

### Redis Connection Issues

Ensure Redis is running and accessible at the configured URL.

### FFmpeg Not Found

FFmpeg is included in the Docker image. For local development, install it:
- macOS: `brew install ffmpeg`
- Ubuntu: `sudo apt-get install ffmpeg`
- Windows: Download from https://ffmpeg.org/download.html

## Next Steps

After setup is complete, you can:
1. Implement database models (Task 2)
2. Set up authentication (Task 3)
3. Build platform adapters (Task 4)
4. Continue with remaining tasks from the implementation plan

## Useful Commands

```bash
# Stop all services
docker-compose down

# Remove all containers and volumes
docker-compose down -v

# Rebuild containers
docker-compose up --build

# View logs for specific service
docker-compose logs -f backend

# Access database
docker-compose exec postgres psql -U postgres -d video_scheduler

# Access Redis CLI
docker-compose exec redis redis-cli
```
