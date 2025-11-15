#!/bin/bash

# Multi-Platform Video Scheduler - Start Script
# Starts all services in the background

set -e

echo "🚀 Starting Multi-Platform Video Scheduler..."
echo ""

# Check if setup has been run
if [ ! -f "backend/.env" ]; then
    echo "❌ Setup not complete. Please run ./setup.sh first"
    exit 1
fi

# Start Docker services if not running
echo "Checking Docker services..."
if ! docker-compose ps | grep -q "postgres.*Up"; then
    echo "Starting PostgreSQL and Redis..."
    docker-compose up -d postgres redis
    sleep 5
fi

echo "✓ Docker services running"
echo ""

# Function to check if port is in use
check_port() {
    lsof -ti:$1 > /dev/null 2>&1
}

# Start backend
echo "Starting backend on port 8000..."
if check_port 8000; then
    echo "⚠ Port 8000 already in use. Backend may already be running."
else
    cd backend
    source venv/bin/activate 2>/dev/null || true
    nohup uvicorn main:app --reload --host 0.0.0.0 --port 8000 > ../logs/backend.log 2>&1 &
    echo $! > ../logs/backend.pid
    cd ..
    echo "✓ Backend started (PID: $(cat logs/backend.pid))"
fi

# Start frontend
echo "Starting frontend on port 3000..."
if check_port 3000; then
    echo "⚠ Port 3000 already in use. Frontend may already be running."
else
    cd frontend
    nohup npm run dev > ../logs/frontend.log 2>&1 &
    echo $! > ../logs/frontend.pid
    cd ..
    echo "✓ Frontend started (PID: $(cat logs/frontend.pid))"
fi

# Start Celery worker (optional)
echo "Starting Celery worker..."
cd backend
source venv/bin/activate 2>/dev/null || true
nohup celery -A src.celery_app worker --loglevel=info > ../logs/celery.log 2>&1 &
echo $! > ../logs/celery.pid
cd ..
echo "✓ Celery worker started (PID: $(cat logs/celery.pid))"

echo ""
echo "================================================"
echo "✅ All services started!"
echo "================================================"
echo ""
echo "Services:"
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo ""
echo "Logs:"
echo "  Backend:   tail -f logs/backend.log"
echo "  Frontend:  tail -f logs/frontend.log"
echo "  Celery:    tail -f logs/celery.log"
echo ""
echo "To stop all services, run: ./stop.sh"
echo ""
