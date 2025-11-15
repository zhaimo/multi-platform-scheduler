# Docker Restart Guide - When Docker is Hung

## Quick Fix (Automated)

Run this script to automatically restart Docker:

```bash
cd multi-platform-scheduler
./restart-docker.sh
```

This will:
1. Stop all containers
2. Kill Docker processes
3. Restart Docker Desktop
4. Wait for Docker to be ready

Then run:
```bash
./start.sh
```

---

## Manual Method (If Script Doesn't Work)

### Option 1: Restart via Docker Desktop UI

1. **Click the Docker whale icon** in your Mac menu bar
2. Select **"Restart"** from the dropdown menu
3. Wait 30-60 seconds for Docker to restart
4. Verify it's running: `docker ps`

### Option 2: Force Quit and Restart

1. **Force quit Docker Desktop**:
   ```bash
   pkill -9 -f Docker
   pkill -9 -f com.docker
   ```

2. **Wait 5 seconds**:
   ```bash
   sleep 5
   ```

3. **Restart Docker Desktop**:
   ```bash
   open -a Docker
   ```

4. **Wait for Docker to start** (30-60 seconds)
   - Watch for the whale icon in menu bar to be steady (not animated)

5. **Verify Docker is running**:
   ```bash
   docker ps
   ```

### Option 3: Complete Docker Reset (Nuclear Option)

⚠️ **Warning**: This will delete all Docker data (containers, images, volumes)

1. **Quit Docker Desktop completely**:
   ```bash
   pkill -9 -f Docker
   ```

2. **Remove Docker data** (optional - only if really stuck):
   ```bash
   rm -rf ~/Library/Containers/com.docker.docker
   rm -rf ~/Library/Application\ Support/Docker\ Desktop
   rm -rf ~/Library/Group\ Containers/group.com.docker
   ```

3. **Restart your Mac** (recommended after removing data)

4. **Open Docker Desktop** from Applications

5. **Wait for initial setup** to complete

---

## After Docker Restarts

### 1. Verify Docker is Working

```bash
docker ps
docker version
```

You should see output without errors.

### 2. Start Project Services

```bash
cd multi-platform-scheduler
./start.sh
```

### 3. Check All Services

```bash
./check-services.sh
```

You should see all green checkmarks.

### 4. Try Registration Again

Go to http://localhost:3000/register

---

## Common Docker Issues on Mac

### Issue: "Docker is starting..." forever

**Solution**:
```bash
pkill -9 -f Docker
open -a Docker
```

### Issue: "Cannot connect to Docker daemon"

**Solution**:
1. Check if Docker Desktop is running (whale icon in menu bar)
2. If not, open it from Applications
3. Wait for it to fully start

### Issue: Docker uses too much CPU/Memory

**Solution**:
1. Open Docker Desktop
2. Go to Settings → Resources
3. Reduce CPU/Memory allocation
4. Click "Apply & Restart"

### Issue: Containers won't start

**Solution**:
```bash
# Remove all containers and start fresh
docker-compose down -v
docker system prune -a --volumes -f
./start.sh
```

### Issue: Port conflicts (5432, 6379, 8000, 3000)

**Solution**:
```bash
# Find what's using the ports
lsof -ti:5432
lsof -ti:6379
lsof -ti:8000
lsof -ti:3000

# Kill processes on those ports
lsof -ti:5432 | xargs kill -9
lsof -ti:6379 | xargs kill -9
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9

# Then start services
./start.sh
```

---

## Checking Docker Status

### Is Docker Running?
```bash
docker ps
```

### Docker Version
```bash
docker version
```

### Docker Info
```bash
docker info
```

### View Docker Logs
```bash
# Mac: View Docker Desktop logs
open ~/Library/Containers/com.docker.docker/Data/log
```

---

## Prevention Tips

1. **Don't run too many containers** - Stop unused containers
2. **Allocate enough resources** - Docker Desktop → Settings → Resources
3. **Keep Docker updated** - Check for updates regularly
4. **Restart Docker weekly** - Prevents memory leaks
5. **Use docker-compose down** - Always stop containers properly

---

## Still Having Issues?

### Check Docker Desktop Logs
1. Open Docker Desktop
2. Click the bug icon (top right)
3. Select "Troubleshoot"
4. View logs

### Reset Docker to Factory Defaults
1. Open Docker Desktop
2. Go to Settings → Troubleshoot
3. Click "Reset to factory defaults"
4. Restart Docker Desktop

### Contact Support
If Docker continues to hang:
1. Check Docker Desktop version (should be latest)
2. Check macOS version compatibility
3. Try reinstalling Docker Desktop
4. Check Docker forums: https://forums.docker.com/

---

## Quick Reference Commands

```bash
# Restart Docker (automated)
./restart-docker.sh

# Check if Docker is running
docker ps

# Stop all containers
docker stop $(docker ps -aq)

# Remove all containers
docker rm $(docker ps -aq)

# Clean up Docker
docker system prune -a --volumes -f

# Start project services
./start.sh

# Check service status
./check-services.sh
```
