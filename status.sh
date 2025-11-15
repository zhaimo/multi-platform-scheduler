#!/bin/bash

# Multi-Platform Video Scheduler - Status Check Script

echo "📊 Multi-Platform Video Scheduler - Status"
echo "==========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check Docker services
echo "Docker Services:"
echo "----------------"

if docker-compose ps | grep -q "postgres.*Up"; then
    echo -e "${GREEN}✓ PostgreSQL: Running${NC}"
else
    echo -e "${RED}✗ PostgreSQL: Not running${NC}"
fi

if docker-compose ps | grep -q "redis.*Up"; then
    echo -e "${GREEN}✓ Redis: Running${NC}"
else
    echo -e "${RED}✗ Redis: Not running${NC}"
fi

echo ""
echo "Application Services:"
echo "---------------------"

# Check backend
if [ -f "logs/backend.pid" ] && kill -0 $(cat logs/backend.pid) 2>/dev/null; then
    echo -e "${GREEN}✓ Backend: Running (PID: $(cat logs/backend.pid))${NC}"
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ Health check: OK${NC}"
    else
        echo -e "  ${YELLOW}⚠ Health check: Failed${NC}"
    fi
else
    echo -e "${RED}✗ Backend: Not running${NC}"
fi

# Check frontend
if [ -f "logs/frontend.pid" ] && kill -0 $(cat logs/frontend.pid) 2>/dev/null; then
    echo -e "${GREEN}✓ Frontend: Running (PID: $(cat logs/frontend.pid))${NC}"
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ Accessible: OK${NC}"
    else
        echo -e "  ${YELLOW}⚠ Accessible: Failed${NC}"
    fi
else
    echo -e "${RED}✗ Frontend: Not running${NC}"
fi

# Check Celery worker
if [ -f "logs/celery.pid" ] && kill -0 $(cat logs/celery.pid) 2>/dev/null; then
    echo -e "${GREEN}✓ Celery Worker: Running (PID: $(cat logs/celery.pid))${NC}"
else
    echo -e "${RED}✗ Celery Worker: Not running${NC}"
fi

echo ""
echo "URLs:"
echo "-----"
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo "  Health:    http://localhost:8000/health"
echo ""

# Check recent logs for errors
echo "Recent Errors:"
echo "--------------"

if [ -f "logs/backend.log" ]; then
    BACKEND_ERRORS=$(grep -i "error" logs/backend.log | tail -3)
    if [ -n "$BACKEND_ERRORS" ]; then
        echo -e "${RED}Backend:${NC}"
        echo "$BACKEND_ERRORS"
    else
        echo -e "${GREEN}Backend: No recent errors${NC}"
    fi
fi

if [ -f "logs/celery.log" ]; then
    CELERY_ERRORS=$(grep -i "error" logs/celery.log | tail -3)
    if [ -n "$CELERY_ERRORS" ]; then
        echo -e "${RED}Celery:${NC}"
        echo "$CELERY_ERRORS"
    else
        echo -e "${GREEN}Celery: No recent errors${NC}"
    fi
fi

echo ""
