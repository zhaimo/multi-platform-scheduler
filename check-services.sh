#!/bin/bash

# Service Health Check Script
# Checks if all required services are running

echo "🔍 Checking Multi-Platform Video Scheduler Services..."
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Docker
echo "1. Checking Docker..."
if docker ps > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓${NC} Docker is running"
else
    echo -e "   ${RED}✗${NC} Docker is NOT running"
    echo -e "   ${YELLOW}→${NC} Please start Docker Desktop and try again"
    exit 1
fi

# Check PostgreSQL container
echo ""
echo "2. Checking PostgreSQL..."
if docker ps | grep -q "video-scheduler-postgres"; then
    echo -e "   ${GREEN}✓${NC} PostgreSQL container is running"
    
    # Check if database is accepting connections
    if docker exec video-scheduler-postgres pg_isready -U postgres > /dev/null 2>&1; then
        echo -e "   ${GREEN}✓${NC} PostgreSQL is accepting connections"
    else
        echo -e "   ${YELLOW}⚠${NC} PostgreSQL container is running but not ready yet"
        echo -e "   ${YELLOW}→${NC} Wait a few seconds and try again"
    fi
else
    echo -e "   ${RED}✗${NC} PostgreSQL container is NOT running"
    echo -e "   ${YELLOW}→${NC} Run: docker-compose up -d postgres"
fi

# Check Redis container
echo ""
echo "3. Checking Redis..."
if docker ps | grep -q "video-scheduler-redis"; then
    echo -e "   ${GREEN}✓${NC} Redis container is running"
else
    echo -e "   ${RED}✗${NC} Redis container is NOT running"
    echo -e "   ${YELLOW}→${NC} Run: docker-compose up -d redis"
fi

# Check Backend
echo ""
echo "4. Checking Backend API..."
if lsof -ti:8000 > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓${NC} Backend is running on port 8000"
    
    # Check health endpoint
    if curl -s http://localhost:8000/health | grep -q "healthy"; then
        echo -e "   ${GREEN}✓${NC} Backend health check passed"
    else
        echo -e "   ${YELLOW}⚠${NC} Backend is running but health check failed"
    fi
else
    echo -e "   ${RED}✗${NC} Backend is NOT running"
    echo -e "   ${YELLOW}→${NC} Run: ./start.sh"
fi

# Check Frontend
echo ""
echo "5. Checking Frontend..."
if lsof -ti:3000 > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓${NC} Frontend is running on port 3000"
else
    echo -e "   ${RED}✗${NC} Frontend is NOT running"
    echo -e "   ${YELLOW}→${NC} Run: ./start.sh"
fi

# Check Celery
echo ""
echo "6. Checking Celery Worker..."
if pgrep -f "celery.*worker" > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓${NC} Celery worker is running"
else
    echo -e "   ${YELLOW}⚠${NC} Celery worker is NOT running"
    echo -e "   ${YELLOW}→${NC} Run: ./start.sh"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Summary
if docker ps | grep -q "video-scheduler-postgres" && \
   docker ps | grep -q "video-scheduler-redis" && \
   lsof -ti:8000 > /dev/null 2>&1 && \
   lsof -ti:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ All critical services are running!${NC}"
    echo ""
    echo "You can now:"
    echo "  • Frontend: http://localhost:3000"
    echo "  • Backend:  http://localhost:8000"
    echo "  • API Docs: http://localhost:8000/docs"
else
    echo -e "${RED}❌ Some services are not running${NC}"
    echo ""
    echo "To start all services, run:"
    echo "  ./start.sh"
fi

echo ""
