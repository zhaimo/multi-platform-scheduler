#!/bin/bash

# Multi-Platform Video Scheduler - Stop Script
# Stops all running services

echo "🛑 Stopping Multi-Platform Video Scheduler..."
echo ""

# Stop backend
if [ -f "logs/backend.pid" ]; then
    PID=$(cat logs/backend.pid)
    if kill -0 $PID 2>/dev/null; then
        echo "Stopping backend (PID: $PID)..."
        kill $PID
        rm logs/backend.pid
        echo "✓ Backend stopped"
    else
        echo "⚠ Backend not running"
        rm logs/backend.pid
    fi
else
    echo "⚠ Backend PID file not found"
fi

# Stop frontend
if [ -f "logs/frontend.pid" ]; then
    PID=$(cat logs/frontend.pid)
    if kill -0 $PID 2>/dev/null; then
        echo "Stopping frontend (PID: $PID)..."
        kill $PID
        rm logs/frontend.pid
        echo "✓ Frontend stopped"
    else
        echo "⚠ Frontend not running"
        rm logs/frontend.pid
    fi
else
    echo "⚠ Frontend PID file not found"
fi

# Stop Celery worker
if [ -f "logs/celery.pid" ]; then
    PID=$(cat logs/celery.pid)
    if kill -0 $PID 2>/dev/null; then
        echo "Stopping Celery worker (PID: $PID)..."
        kill $PID
        rm logs/celery.pid
        echo "✓ Celery worker stopped"
    else
        echo "⚠ Celery worker not running"
        rm logs/celery.pid
    fi
else
    echo "⚠ Celery PID file not found"
fi

# Stop Docker services
echo "Stopping Docker services..."
docker-compose stop postgres redis
echo "✓ Docker services stopped"

echo ""
echo "✅ All services stopped"
echo ""
