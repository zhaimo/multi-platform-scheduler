# Multi-Platform Video Scheduler

A web application that enables content creators to upload, schedule, and post short-form videos across multiple social media platforms (TikTok, YouTube Shorts, Instagram Reels, Facebook) simultaneously.

## Features

- Upload videos once and post to multiple platforms
- Schedule posts for optimal engagement times
- Repost previously published content
- Automatic video format conversion
- Platform-specific customization (captions, hashtags)
- Analytics tracking across platforms
- Recurring post schedules

## Tech Stack

### Backend
- **Framework**: FastAPI
- **Database**: PostgreSQL
- **Task Queue**: Celery + Redis
- **Storage**: AWS S3
- **Video Processing**: FFmpeg

### Frontend
- **Framework**: Next.js 14 (React)
- **Language**: TypeScript
- **Styling**: Tailwind CSS

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Node.js 20+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Quick Start with Docker

1. Clone the repository
2. Copy environment files:
   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   ```

3. Update the `.env` files with your configuration

4. Start all services:
   ```bash
   docker-compose up
   ```

5. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Local Development

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
multi-platform-scheduler/
├── backend/
│   ├── src/
│   │   ├── api/          # API routes
│   │   ├── services/     # Business logic
│   │   ├── models/       # Database models
│   │   ├── adapters/     # Platform adapters
│   │   ├── utils/        # Utilities
│   │   ├── config.py     # Configuration
│   │   ├── celery_app.py # Celery setup
│   │   └── tasks.py      # Background tasks
│   ├── tests/            # Tests
│   ├── main.py           # FastAPI app
│   └── requirements.txt  # Python dependencies
├── frontend/
│   ├── app/              # Next.js app directory
│   ├── components/       # React components
│   └── lib/              # Utilities
└── docker-compose.yml    # Docker orchestration
```

## Configuration

### Backend Environment Variables

See `backend/.env.example` for all available configuration options.

Key variables:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`: AWS credentials
- `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`: TikTok API credentials
- Platform API credentials for YouTube, Instagram, Facebook

### Frontend Environment Variables

See `frontend/.env.example` for configuration options.

## Documentation

- **[Setup Guide](./SETUP.md)** - Detailed setup instructions
- **[Environment Variables](./ENVIRONMENT_VARIABLES.md)** - Complete environment variable reference
- **[Deployment Guide](./DEPLOYMENT_GUIDE.md)** - AWS and Vercel deployment instructions
- **[Troubleshooting](./TROUBLESHOOTING.md)** - Common issues and solutions
- **[Database Setup](./backend/DATABASE_SETUP.md)** - Database configuration
- **[Docker Guide](./DOCKER.md)** - Docker deployment details
- **[CI/CD](./CI_CD.md)** - Continuous integration and deployment
- **[Security](./backend/SECURITY.md)** - Security best practices
- **[Frontend Guide](./frontend/FRONTEND_GUIDE.md)** - Frontend development guide

## API Documentation

Once the backend is running, visit http://localhost:8000/docs for interactive API documentation.

## Platform Setup

Before using the application, you'll need to set up developer accounts and obtain API credentials for each platform:

- **TikTok**: [TikTok for Developers](https://developers.tiktok.com/)
- **YouTube**: [Google Cloud Console](https://console.cloud.google.com/)
- **Instagram**: [Meta for Developers](https://developers.facebook.com/)
- **Facebook**: [Meta for Developers](https://developers.facebook.com/)

Refer to the [Deployment Guide](./DEPLOYMENT_GUIDE.md) for detailed platform configuration instructions.

## License

MIT
