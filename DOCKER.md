# Docker Configuration Guide

This document explains the Docker setup for the Multi-Platform Video Scheduler.

## Overview

The application uses Docker containers for all services:

- **Backend**: FastAPI application (Python)
- **Frontend**: Next.js application (Node.js)
- **PostgreSQL**: Primary database
- **Redis**: Job queue and caching
- **Celery Worker**: Background job processor
- **Celery Beat**: Scheduled task scheduler

## Docker Files

### Development

- `Dockerfile` (backend) - Development backend image
- `Dockerfile` (frontend) - Development frontend image
- `docker-compose.yml` - Development orchestration

### Production

- `Dockerfile.prod` (backend) - Production-optimized backend image
- `Dockerfile.worker` (backend) - Production Celery worker image
- `Dockerfile.prod` (frontend) - Production-optimized frontend image
- `docker-compose.prod.yml` - Production orchestration

## Key Differences: Development vs Production

### Development Setup

**Features:**
- Hot reload enabled for both backend and frontend
- Source code mounted as volumes for live editing
- Debug logging enabled
- No resource limits
- Single worker processes
- Development dependencies included

**Usage:**
```bash
# Start development environment
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Production Setup

**Features:**
- Multi-stage builds for smaller images
- No source code mounting (baked into image)
- Production logging (JSON format)
- Resource limits configured
- Multiple worker processes
- Health checks on all services
- Non-root users for security
- Optimized dependencies only
- Automatic restarts

**Usage:**
```bash
# Start production environment
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop
docker-compose -f docker-compose.prod.yml down
```

## Container Details

### Backend Container

**Base Image:** `python:3.11-slim`

**Key Features:**
- Multi-stage build (builder + runtime)
- FFmpeg installed for video processing
- Non-root user (appuser, UID 1000)
- 4 Uvicorn workers in production
- Health check via `/health` endpoint

**Ports:** 8000

**Environment Variables:**
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `JWT_SECRET_KEY` - JWT signing key
- `AWS_*` - AWS credentials for S3
- `ENCRYPTION_KEY` - For encrypting platform tokens

### Frontend Container

**Base Image:** `node:20-alpine`

**Key Features:**
- Multi-stage build (builder + runtime)
- Production build with optimizations
- Non-root user (appuser, UID 1000)
- Static asset optimization
- Health check via HTTP request

**Ports:** 3000

**Environment Variables:**
- `NEXT_PUBLIC_API_URL` - Backend API URL
- `NODE_ENV` - Set to 'production'

### Celery Worker Container

**Base Image:** `python:3.11-slim`

**Key Features:**
- Same base as backend
- FFmpeg for video processing
- Configurable concurrency (default: 4)
- Health check via Celery inspect
- Can be horizontally scaled

**Environment Variables:**
- Same as backend
- `CELERY_BROKER_URL` - Redis broker URL
- `CELERY_RESULT_BACKEND` - Redis results URL

### PostgreSQL Container

**Base Image:** `postgres:15-alpine`

**Key Features:**
- Data persistence via volume
- Health check via `pg_isready`
- Configurable credentials
- Resource limits in production

**Ports:** 5432

**Volume:** `postgres_data`

### Redis Container

**Base Image:** `redis:7-alpine`

**Key Features:**
- Data persistence via volume
- AOF (Append Only File) enabled
- Password protection in production
- Health check via `redis-cli ping`

**Ports:** 6379

**Volume:** `redis_data`

## Health Checks

All production containers include health checks:

### Backend
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)"
```

### Frontend
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1
```

### Celery Worker
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD celery -A src.celery_app inspect ping -d celery@$HOSTNAME || exit 1
```

### PostgreSQL
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U postgres"]
  interval: 10s
  timeout: 5s
  retries: 5
```

### Redis
```yaml
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 10s
  timeout: 5s
  retries: 5
```

## Resource Limits

Production containers have resource limits to prevent overconsumption:

```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
    reservations:
      cpus: '1'
      memory: 1G
```

Adjust these based on your server capacity and load requirements.

## Networking

All containers communicate via a dedicated bridge network:

```yaml
networks:
  video-scheduler-network:
    driver: bridge
```

**Internal DNS:**
- Backend: `backend:8000`
- Frontend: `frontend:3000`
- PostgreSQL: `postgres:5432`
- Redis: `redis:6379`

## Volumes

### Persistent Volumes

```yaml
volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
```

**Location:** `/var/lib/docker/volumes/`

### Development Volumes

Source code is mounted for live editing:

```yaml
volumes:
  - ./backend:/app
  - ./frontend:/app
```

## Security Features

### Non-Root Users

All application containers run as non-root users:

```dockerfile
RUN useradd -m -u 1000 appuser
USER appuser
```

### Secrets Management

Sensitive data is passed via environment variables, never hardcoded:

- Database passwords
- API keys
- JWT secrets
- Encryption keys

### Network Isolation

Containers communicate only via the internal network. Only necessary ports are exposed to the host.

### Image Optimization

Multi-stage builds reduce attack surface:

```dockerfile
FROM python:3.11-slim as builder
# Build dependencies

FROM python:3.11-slim
# Runtime only
```

## Logging

### Log Drivers

Production uses JSON file logging with rotation:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### Viewing Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f backend

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 backend

# Follow with timestamps
docker-compose -f docker-compose.prod.yml logs -f -t backend
```

## Scaling

### Horizontal Scaling

Scale Celery workers:

```bash
# Scale to 4 workers
docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=4

# Using Makefile
make scale-workers
# Enter: 4
```

### Vertical Scaling

Adjust resource limits in `docker-compose.prod.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 4G
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs backend

# Check container status
docker-compose -f docker-compose.prod.yml ps

# Inspect container
docker inspect video-scheduler-backend-prod
```

### Health Check Failing

```bash
# Check health status
docker inspect --format='{{json .State.Health}}' video-scheduler-backend-prod | python3 -m json.tool

# Manual health check
docker-compose -f docker-compose.prod.yml exec backend curl http://localhost:8000/health
```

### Network Issues

```bash
# List networks
docker network ls

# Inspect network
docker network inspect multi-platform-scheduler_video-scheduler-network

# Test connectivity
docker-compose -f docker-compose.prod.yml exec backend ping postgres
```

### Volume Issues

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect multi-platform-scheduler_postgres_data

# Remove volume (CAUTION: deletes data)
docker volume rm multi-platform-scheduler_postgres_data
```

### Out of Memory

```bash
# Check memory usage
docker stats

# Adjust limits in docker-compose.prod.yml
# Restart services
docker-compose -f docker-compose.prod.yml up -d
```

## Best Practices

### 1. Use .dockerignore

Exclude unnecessary files from build context:

```
node_modules/
.git/
*.log
.env
```

### 2. Multi-Stage Builds

Separate build and runtime stages for smaller images.

### 3. Layer Caching

Order Dockerfile commands from least to most frequently changing:

```dockerfile
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
```

### 4. Health Checks

Always include health checks for production containers.

### 5. Resource Limits

Set appropriate CPU and memory limits.

### 6. Logging

Configure log rotation to prevent disk space issues.

### 7. Security

- Run as non-root user
- Use secrets management
- Keep base images updated
- Scan images for vulnerabilities

### 8. Monitoring

- Monitor container health
- Track resource usage
- Set up alerts for failures

## Useful Commands

```bash
# Build without cache
docker-compose -f docker-compose.prod.yml build --no-cache

# Remove all stopped containers
docker container prune

# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# View container processes
docker-compose -f docker-compose.prod.yml top

# Execute command in container
docker-compose -f docker-compose.prod.yml exec backend bash

# Copy files from container
docker cp video-scheduler-backend-prod:/app/logs ./logs

# View container resource usage
docker stats --no-stream
```

## References

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Best Practices for Writing Dockerfiles](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Docker Security](https://docs.docker.com/engine/security/)
