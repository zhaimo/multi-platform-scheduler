# Production Deployment Guide

This guide covers deploying the Multi-Platform Video Scheduler to production using Docker.

## Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- Domain name with DNS configured
- SSL/TLS certificates (Let's Encrypt recommended)
- AWS account with S3 bucket created
- Platform API credentials (TikTok, YouTube, Instagram, Facebook)

## Quick Start

### 1. Clone and Configure

```bash
# Clone the repository
git clone <repository-url>
cd multi-platform-scheduler

# Copy production environment file
cp backend/.env.production.example backend/.env.production

# Edit with your production values
nano backend/.env.production
```

### 2. Generate Secure Keys

```bash
# Generate JWT secret key (min 32 characters)
openssl rand -hex 32

# Generate encryption key (32 bytes, base64 encoded)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Generate secure passwords for PostgreSQL and Redis
openssl rand -base64 32
```

### 3. Configure Environment Variables

Edit `backend/.env.production` and set all required values:

**Critical Variables:**
- `POSTGRES_PASSWORD` - Strong password for PostgreSQL
- `REDIS_PASSWORD` - Strong password for Redis
- `JWT_SECRET_KEY` - Random 32+ character string
- `ENCRYPTION_KEY` - Base64-encoded 32-byte key
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` - AWS credentials
- `S3_BUCKET_NAME` - Your S3 bucket name
- Platform API credentials (TikTok, YouTube, Instagram, Facebook)
- `SENTRY_DSN` - For error tracking (optional but recommended)

### 4. Build and Start Services

```bash
# Build all containers
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Check service health
docker-compose -f docker-compose.prod.yml ps
```

### 5. Run Database Migrations

```bash
# Run Alembic migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### 6. Verify Deployment

```bash
# Check backend health
curl http://localhost:8000/health

# Check frontend
curl http://localhost:3000

# View logs
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f celery-worker
```

## Architecture Overview

### Services

1. **PostgreSQL** - Primary database
   - Port: 5432
   - Volume: `postgres_data`
   - Health check: `pg_isready`

2. **Redis** - Job queue and cache
   - Port: 6379
   - Volume: `redis_data`
   - Health check: `redis-cli ping`

3. **Backend** - FastAPI application
   - Port: 8000
   - Workers: 4 (uvicorn)
   - Health check: `/health` endpoint

4. **Celery Worker** - Background job processor
   - Replicas: 2 (configurable)
   - Concurrency: 4 per worker
   - Health check: Celery inspect ping

5. **Celery Beat** - Scheduled task scheduler
   - Single instance
   - Manages recurring jobs

6. **Frontend** - Next.js application
   - Port: 3000
   - Production build
   - Health check: HTTP request to `/`

### Network

All services communicate via the `video-scheduler-network` bridge network.

### Volumes

- `postgres_data` - PostgreSQL data persistence
- `redis_data` - Redis data persistence

## Resource Limits

Default resource allocations:

| Service | CPU Limit | Memory Limit | CPU Reserved | Memory Reserved |
|---------|-----------|--------------|--------------|-----------------|
| PostgreSQL | 2 | 2GB | 1 | 1GB |
| Redis | 1 | 1GB | 0.5 | 512MB |
| Backend | 2 | 2GB | 1 | 1GB |
| Celery Worker | 2 | 2GB | 1 | 1GB |
| Celery Beat | 0.5 | 512MB | 0.25 | 256MB |
| Frontend | 1 | 1GB | 0.5 | 512MB |

Adjust in `docker-compose.prod.yml` based on your server capacity.

## Scaling

### Horizontal Scaling

Scale Celery workers for increased job processing:

```bash
docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=4
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

## SSL/TLS Configuration

### Option 1: Nginx Reverse Proxy (Recommended)

Create `nginx.conf`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # File upload size limit
    client_max_body_size 500M;
}
```

### Option 2: Traefik (Alternative)

Add Traefik service to `docker-compose.prod.yml` for automatic SSL with Let's Encrypt.

## Monitoring

### Health Checks

All services include health checks:

```bash
# Check all service health
docker-compose -f docker-compose.prod.yml ps

# Individual service health
docker inspect --format='{{.State.Health.Status}}' video-scheduler-backend-prod
```

### Logs

```bash
# View all logs
docker-compose -f docker-compose.prod.yml logs -f

# Specific service logs
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f celery-worker

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 backend
```

### Sentry Integration

Configure Sentry DSN in `.env.production` for error tracking:

```bash
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

## Backup and Recovery

### Database Backup

```bash
# Create backup
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres video_scheduler > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U postgres video_scheduler < backup_20231115_120000.sql
```

### Automated Backups

Add to crontab:

```bash
# Daily backup at 2 AM
0 2 * * * cd /path/to/multi-platform-scheduler && docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres video_scheduler > /backups/db_$(date +\%Y\%m\%d).sql
```

### Volume Backup

```bash
# Backup PostgreSQL volume
docker run --rm -v video-scheduler_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_data_backup.tar.gz -C /data .

# Restore PostgreSQL volume
docker run --rm -v video-scheduler_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres_data_backup.tar.gz -C /data
```

## Maintenance

### Update Application

```bash
# Pull latest code
git pull origin main

# Rebuild containers
docker-compose -f docker-compose.prod.yml build

# Restart services with zero downtime
docker-compose -f docker-compose.prod.yml up -d --no-deps --build backend
docker-compose -f docker-compose.prod.yml up -d --no-deps --build celery-worker
docker-compose -f docker-compose.prod.yml up -d --no-deps --build frontend

# Run migrations if needed
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### Database Migrations

```bash
# Check current migration version
docker-compose -f docker-compose.prod.yml exec backend alembic current

# Upgrade to latest
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Rollback one version
docker-compose -f docker-compose.prod.yml exec backend alembic downgrade -1
```

### Clean Up

```bash
# Remove stopped containers
docker-compose -f docker-compose.prod.yml down

# Remove containers and volumes (CAUTION: deletes data)
docker-compose -f docker-compose.prod.yml down -v

# Clean up unused images
docker image prune -a
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs backend

# Check service status
docker-compose -f docker-compose.prod.yml ps

# Restart specific service
docker-compose -f docker-compose.prod.yml restart backend
```

### Database Connection Issues

```bash
# Verify PostgreSQL is running
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U postgres

# Check connection from backend
docker-compose -f docker-compose.prod.yml exec backend python -c "from src.database import engine; print('Connected')"
```

### Celery Worker Issues

```bash
# Check worker status
docker-compose -f docker-compose.prod.yml exec celery-worker celery -A src.celery_app inspect active

# Check registered tasks
docker-compose -f docker-compose.prod.yml exec celery-worker celery -A src.celery_app inspect registered

# Purge all tasks (CAUTION)
docker-compose -f docker-compose.prod.yml exec celery-worker celery -A src.celery_app purge
```

### High Memory Usage

```bash
# Check resource usage
docker stats

# Adjust resource limits in docker-compose.prod.yml
# Restart services
docker-compose -f docker-compose.prod.yml up -d
```

### Video Upload Failures

1. Check S3 credentials and permissions
2. Verify S3 bucket exists and is accessible
3. Check disk space on host machine
4. Review backend logs for specific errors

## Security Checklist

- [ ] Strong passwords for PostgreSQL and Redis
- [ ] JWT secret key is random and secure (32+ chars)
- [ ] Encryption key is properly generated
- [ ] AWS credentials have minimal required permissions
- [ ] Platform API credentials are valid
- [ ] Firewall configured (only ports 80, 443 exposed)
- [ ] SSL/TLS certificates installed
- [ ] Sentry DSN configured for error tracking
- [ ] Regular backups scheduled
- [ ] Log rotation configured
- [ ] Non-root users in containers
- [ ] Environment files not committed to git

## Performance Optimization

### Database

```sql
-- Create indexes for frequently queried fields
CREATE INDEX idx_posts_user_id ON posts(user_id);
CREATE INDEX idx_posts_status ON posts(status);
CREATE INDEX idx_videos_user_id ON videos(user_id);
CREATE INDEX idx_schedules_scheduled_at ON schedules(scheduled_at);
```

### Redis

Configure Redis persistence:

```bash
# In docker-compose.prod.yml, update Redis command:
command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD} --maxmemory 512mb --maxmemory-policy allkeys-lru
```

### Celery

Adjust worker concurrency based on CPU cores:

```bash
# In docker-compose.prod.yml
command: celery -A src.celery_app worker --loglevel=info --concurrency=8
```

## Support

For issues and questions:
- Check logs: `docker-compose -f docker-compose.prod.yml logs`
- Review health checks: `docker-compose -f docker-compose.prod.yml ps`
- Consult application documentation
- Check Sentry for error reports
