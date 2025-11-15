# CI/CD Pipeline Documentation

This document describes the Continuous Integration and Continuous Deployment (CI/CD) pipeline for the Multi-Platform Video Scheduler.

## Overview

The CI/CD pipeline uses GitHub Actions to automate testing, building, and deployment processes. The pipeline consists of four main workflows:

1. **Test** - Runs automated tests on every push and pull request
2. **Build** - Builds Docker images and pushes to container registry
3. **Deploy to Staging** - Automatically deploys to staging environment
4. **Deploy to Production** - Deploys to production on release

## Workflows

### 1. Test Workflow (`test.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

**Jobs:**

#### test-backend
- Sets up Python 3.11
- Starts PostgreSQL and Redis services
- Installs FFmpeg and dependencies
- Runs pytest with coverage
- Uploads coverage to Codecov

#### test-frontend
- Sets up Node.js 20
- Installs dependencies
- Runs linter
- Builds the application

#### lint-backend
- Runs flake8 for code quality
- Checks black formatting
- Checks isort import ordering

**Environment Variables Required:**
- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET_KEY`
- `ENCRYPTION_KEY`
- AWS credentials (for testing)

### 2. Build Workflow (`build.yml`)

**Triggers:**
- Push to `main` branch
- Tags matching `v*` pattern
- Pull requests to `main` branch

**Jobs:**

#### build-backend
- Builds production backend Docker image
- Pushes to GitHub Container Registry (ghcr.io)
- Tags: branch name, PR number, semver, SHA

#### build-worker
- Builds Celery worker Docker image
- Pushes to GitHub Container Registry
- Same tagging strategy as backend

#### build-frontend
- Builds production frontend Docker image
- Pushes to GitHub Container Registry
- Same tagging strategy as backend

**Permissions Required:**
- `contents: read`
- `packages: write`

**Registry:** GitHub Container Registry (ghcr.io)

### 3. Deploy to Staging Workflow (`deploy-staging.yml`)

**Triggers:**
- Push to `develop` branch
- Manual workflow dispatch

**Environment:** staging

**Steps:**
1. Build and push Docker images with `staging` tag
2. SSH into staging server
3. Pull latest images
4. Run database migrations
5. Restart services with zero downtime
6. Perform health check
7. Send Slack notification

**Secrets Required:**
- `STAGING_SSH_KEY` - SSH private key for staging server
- `STAGING_HOST` - Staging server hostname/IP
- `STAGING_USER` - SSH username
- `SLACK_WEBHOOK` - Slack webhook URL for notifications

**Server Requirements:**
- Docker and Docker Compose installed
- Application directory at `/opt/video-scheduler`
- SSH access configured

### 4. Deploy to Production Workflow (`deploy-production.yml`)

**Triggers:**
- Release published
- Manual workflow dispatch with version input

**Environment:** production

**Steps:**
1. Checkout specific version/tag
2. Build and push Docker images with version and `latest` tags
3. Create database backup
4. SSH into production server
5. Pull versioned images
6. Run database migrations
7. Restart services with zero downtime
8. Perform health checks (5 attempts)
9. Rollback on failure
10. Send Slack notification

**Secrets Required:**
- `PROD_SSH_KEY` - SSH private key for production server
- `PROD_HOST` - Production server hostname/IP
- `PROD_USER` - SSH username
- `SLACK_WEBHOOK` - Slack webhook URL for notifications

**Safety Features:**
- Automatic database backup before deployment
- Health check validation
- Automatic rollback on failure
- Manual approval required (GitHub environment protection)

## Setup Instructions

### 1. Configure GitHub Secrets

Navigate to your repository settings → Secrets and variables → Actions

**Required Secrets:**

```
# Staging
STAGING_SSH_KEY=<private-ssh-key>
STAGING_HOST=staging.your-domain.com
STAGING_USER=deploy

# Production
PROD_SSH_KEY=<private-ssh-key>
PROD_HOST=your-domain.com
PROD_USER=deploy

# Notifications
SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Optional
CODECOV_TOKEN=<codecov-token>
```

### 2. Configure GitHub Environments

Create two environments in repository settings:

#### Staging Environment
- Name: `staging`
- URL: `https://staging.your-domain.com`
- No protection rules (auto-deploy)

#### Production Environment
- Name: `production`
- URL: `https://your-domain.com`
- Protection rules:
  - Required reviewers: 1-2 people
  - Wait timer: 5 minutes (optional)
  - Deployment branches: `main` only

### 3. Set Up Deployment Servers

#### Staging Server

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create application directory
sudo mkdir -p /opt/video-scheduler
sudo chown $USER:$USER /opt/video-scheduler
cd /opt/video-scheduler

# Clone repository
git clone <repository-url> .

# Copy environment file
cp backend/.env.production.example backend/.env.production
# Edit with staging values
nano backend/.env.production

# Create docker-compose.staging.yml
cp docker-compose.prod.yml docker-compose.staging.yml
# Adjust as needed for staging
```

#### Production Server

Same steps as staging, but use production environment values.

### 4. Configure SSH Access

On your local machine:

```bash
# Generate SSH key for deployment
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/deploy_key

# Copy public key to servers
ssh-copy-id -i ~/.ssh/deploy_key.pub deploy@staging.your-domain.com
ssh-copy-id -i ~/.ssh/deploy_key.pub deploy@your-domain.com

# Add private key to GitHub secrets
cat ~/.ssh/deploy_key
# Copy output to STAGING_SSH_KEY and PROD_SSH_KEY
```

On deployment servers:

```bash
# Create deploy user
sudo useradd -m -s /bin/bash deploy
sudo usermod -aG docker deploy

# Set up SSH
sudo mkdir -p /home/deploy/.ssh
sudo cp ~/.ssh/authorized_keys /home/deploy/.ssh/
sudo chown -R deploy:deploy /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys

# Grant sudo access for Docker commands (if needed)
sudo visudo
# Add: deploy ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/local/bin/docker-compose
```

### 5. Configure Container Registry

The workflows use GitHub Container Registry (ghcr.io) by default.

**Enable GitHub Packages:**
1. Go to repository settings
2. Enable "Packages" in features
3. Set package visibility (private recommended)

**Alternative: Use Docker Hub**

Update workflows to use Docker Hub:

```yaml
env:
  REGISTRY: docker.io
  IMAGE_NAME: your-dockerhub-username/video-scheduler
```

Add Docker Hub credentials to secrets:
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

Update login action:
```yaml
- name: Log in to Docker Hub
  uses: docker/login-action@v3
  with:
    username: ${{ secrets.DOCKERHUB_USERNAME }}
    password: ${{ secrets.DOCKERHUB_TOKEN }}
```

## Deployment Process

### Staging Deployment

**Automatic:**
1. Push to `develop` branch
2. GitHub Actions runs tests
3. Builds Docker images
4. Deploys to staging automatically
5. Sends Slack notification

**Manual:**
1. Go to Actions tab
2. Select "Deploy to Staging" workflow
3. Click "Run workflow"
4. Select branch
5. Click "Run workflow" button

### Production Deployment

**Via Release:**
1. Create a new release on GitHub
2. Tag format: `v1.0.0` (semantic versioning)
3. Publish release
4. GitHub Actions triggers deployment
5. Requires manual approval (if configured)
6. Deploys to production
7. Sends Slack notification

**Manual:**
1. Go to Actions tab
2. Select "Deploy to Production" workflow
3. Click "Run workflow"
4. Enter version to deploy (e.g., `v1.0.0`)
5. Click "Run workflow" button
6. Approve deployment (if required)

## Monitoring Deployments

### GitHub Actions UI

View workflow runs:
1. Go to repository → Actions tab
2. Select workflow
3. View run details, logs, and status

### Slack Notifications

Deployment notifications include:
- Workflow name
- Status (success/failure)
- Version deployed
- Environment (staging/production)
- Link to workflow run

### Health Checks

After deployment, workflows perform health checks:

```bash
# Backend health
curl https://your-domain.com/health

# Expected response
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "redis": "connected"
}
```

## Rollback Procedures

### Automatic Rollback

Production deployment automatically rolls back if:
- Health checks fail after 5 attempts
- Any deployment step fails

### Manual Rollback

#### Option 1: Redeploy Previous Version

```bash
# Trigger manual deployment with previous version
# Go to Actions → Deploy to Production → Run workflow
# Enter previous version tag (e.g., v1.0.0)
```

#### Option 2: SSH Rollback

```bash
# SSH into production server
ssh deploy@your-domain.com

cd /opt/video-scheduler

# Pull previous image version
docker pull ghcr.io/your-org/video-scheduler-backend:v1.0.0
docker pull ghcr.io/your-org/video-scheduler-worker:v1.0.0
docker pull ghcr.io/your-org/video-scheduler-frontend:v1.0.0

# Update docker-compose
export BACKEND_IMAGE=ghcr.io/your-org/video-scheduler-backend:v1.0.0
export WORKER_IMAGE=ghcr.io/your-org/video-scheduler-worker:v1.0.0
export FRONTEND_IMAGE=ghcr.io/your-org/video-scheduler-frontend:v1.0.0

# Restart services
docker-compose -f docker-compose.prod.yml up -d --no-deps backend celery-worker frontend

# Rollback database if needed
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U postgres video_scheduler < backups/pre_deploy_20231115_120000.sql
```

## Troubleshooting

### Workflow Fails at Test Stage

**Common Issues:**
- Database connection failure
- Missing environment variables
- Test failures

**Solutions:**
```bash
# Run tests locally
cd multi-platform-scheduler/backend
pytest tests/ -v

# Check environment variables in workflow
# Ensure all required secrets are set
```

### Docker Build Fails

**Common Issues:**
- Dockerfile syntax errors
- Missing dependencies
- Build context issues

**Solutions:**
```bash
# Test build locally
docker build -f backend/Dockerfile.prod backend/

# Check build logs in GitHub Actions
# Verify all files are included (check .dockerignore)
```

### Deployment Fails at SSH Step

**Common Issues:**
- SSH key not configured
- Server unreachable
- Permission denied

**Solutions:**
```bash
# Test SSH connection
ssh -i ~/.ssh/deploy_key deploy@your-domain.com

# Verify SSH key in GitHub secrets
# Check server firewall rules
# Verify deploy user permissions
```

### Health Check Fails

**Common Issues:**
- Service not started
- Database migration failed
- Configuration error

**Solutions:**
```bash
# SSH into server
ssh deploy@your-domain.com

# Check service status
cd /opt/video-scheduler
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs backend

# Manual health check
curl http://localhost:8000/health
```

### Database Migration Fails

**Common Issues:**
- Migration conflicts
- Database connection error
- Schema changes incompatible

**Solutions:**
```bash
# SSH into server
ssh deploy@your-domain.com

# Check migration status
cd /opt/video-scheduler
docker-compose -f docker-compose.prod.yml exec backend alembic current

# View migration history
docker-compose -f docker-compose.prod.yml exec backend alembic history

# Manually run migration
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Rollback migration if needed
docker-compose -f docker-compose.prod.yml exec backend alembic downgrade -1
```

## Best Practices

### 1. Branch Strategy

- `main` - Production-ready code
- `develop` - Integration branch for staging
- `feature/*` - Feature branches
- `hotfix/*` - Emergency fixes

### 2. Versioning

Use semantic versioning (semver):
- `v1.0.0` - Major release
- `v1.1.0` - Minor release (new features)
- `v1.1.1` - Patch release (bug fixes)

### 3. Testing

- Write tests for all new features
- Maintain >80% code coverage
- Run tests locally before pushing
- Fix failing tests immediately

### 4. Deployment

- Always deploy to staging first
- Test thoroughly in staging
- Deploy to production during low-traffic hours
- Have rollback plan ready
- Monitor after deployment

### 5. Security

- Rotate SSH keys regularly
- Use environment-specific secrets
- Never commit secrets to repository
- Review deployment logs for sensitive data
- Keep dependencies updated

## Environment Variables

### Required for CI/CD

```bash
# GitHub Secrets
STAGING_SSH_KEY=<ssh-private-key>
STAGING_HOST=staging.example.com
STAGING_USER=deploy
PROD_SSH_KEY=<ssh-private-key>
PROD_HOST=example.com
PROD_USER=deploy
SLACK_WEBHOOK=https://hooks.slack.com/...

# Optional
CODECOV_TOKEN=<token>
DOCKERHUB_USERNAME=<username>
DOCKERHUB_TOKEN=<token>
```

### Required on Servers

See `backend/.env.production.example` for complete list.

## Support

For CI/CD issues:
1. Check workflow logs in GitHub Actions
2. Review this documentation
3. Test locally before pushing
4. Contact DevOps team

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Documentation](https://docs.docker.com/)
- [Semantic Versioning](https://semver.org/)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
