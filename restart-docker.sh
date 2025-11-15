#!/bin/bash

# Force Restart Docker Script
# Use this when Docker is hung or not responding

echo "🔄 Force Restarting Docker..."
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Stop all our containers forcefully
echo "1. Stopping all project containers..."
docker-compose down --remove-orphans 2>/dev/null || echo "   (docker-compose not responding, continuing...)"
docker stop $(docker ps -aq) 2>/dev/null || echo "   (no containers to stop)"
echo -e "   ${GREEN}✓${NC} Containers stopped"

# Step 2: Kill Docker processes
echo ""
echo "2. Killing Docker processes..."
pkill -9 -f Docker 2>/dev/null || echo "   (no Docker processes found)"
pkill -9 -f com.docker 2>/dev/null || echo "   (no Docker processes found)"
echo -e "   ${GREEN}✓${NC} Docker processes killed"

# Step 3: Wait a moment
echo ""
echo "3. Waiting for cleanup..."
sleep 3
echo -e "   ${GREEN}✓${NC} Cleanup complete"

# Step 4: Restart Docker Desktop
echo ""
echo "4. Restarting Docker Desktop..."
echo -e "   ${YELLOW}→${NC} Opening Docker Desktop..."
open -a Docker

# Step 5: Wait for Docker to start
echo ""
echo "5. Waiting for Docker to start..."
echo "   This may take 30-60 seconds..."

MAX_WAIT=60
COUNTER=0
while [ $COUNTER -lt $MAX_WAIT ]; do
    if docker ps > /dev/null 2>&1; then
        echo -e "   ${GREEN}✓${NC} Docker is running!"
        break
    fi
    sleep 2
    COUNTER=$((COUNTER + 2))
    echo -n "."
done

echo ""

if docker ps > /dev/null 2>&1; then
    echo ""
    echo -e "${GREEN}✅ Docker restarted successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Run: ./start.sh"
    echo "  2. Wait for all services to start"
    echo "  3. Try registration again at http://localhost:3000/register"
else
    echo ""
    echo -e "${RED}❌ Docker did not start automatically${NC}"
    echo ""
    echo "Manual steps:"
    echo "  1. Open Docker Desktop manually from Applications"
    echo "  2. Wait for the whale icon to be steady in menu bar"
    echo "  3. Run: ./start.sh"
fi

echo ""
