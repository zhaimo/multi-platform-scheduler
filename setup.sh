#!/bin/bash

# Multi-Platform Video Scheduler - Quick Setup Script
# This script sets up your development environment

set -e  # Exit on error

echo "🚀 Multi-Platform Video Scheduler - Quick Setup"
echo "================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ Error: docker-compose.yml not found${NC}"
    echo "Please run this script from the multi-platform-scheduler directory"
    exit 1
fi

echo "Step 1: Setting up environment files..."
echo "----------------------------------------"

# Backend .env
if [ ! -f "backend/.env" ]; then
    echo "Creating backend/.env from template..."
    cp backend/.env.example backend/.env
    
    # Generate secret keys
    echo "Generating secure keys..."
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32)[:32])")
    
    # Update .env file with generated keys
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" backend/.env
        sed -i '' "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$JWT_SECRET/" backend/.env
        sed -i '' "s/ENCRYPTION_KEY=.*/ENCRYPTION_KEY=$ENCRYPTION_KEY/" backend/.env
    else
        # Linux
        sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" backend/.env
        sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$JWT_SECRET/" backend/.env
        sed -i "s/ENCRYPTION_KEY=.*/ENCRYPTION_KEY=$ENCRYPTION_KEY/" backend/.env
    fi
    
    echo -e "${GREEN}✓ Backend .env created with secure keys${NC}"
else
    echo -e "${YELLOW}⚠ backend/.env already exists, skipping${NC}"
fi

# Frontend .env
if [ ! -f "frontend/.env" ]; then
    echo "Creating frontend/.env from template..."
    cp frontend/.env.example frontend/.env
    echo -e "${GREEN}✓ Frontend .env created${NC}"
else
    echo -e "${YELLOW}⚠ frontend/.env already exists, skipping${NC}"
fi

echo ""
echo "Step 2: Checking Docker services..."
echo "------------------------------------"

# Check if Docker is available
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo "Docker found, starting services..."
    docker-compose up -d postgres redis
    
    # Wait for services to be ready
    echo "Waiting for services to start (10 seconds)..."
    sleep 10
    
    # Check if services are running
    if docker-compose ps | grep -q "postgres.*Up"; then
        echo -e "${GREEN}✓ PostgreSQL is running${NC}"
    else
        echo -e "${RED}❌ PostgreSQL failed to start${NC}"
        exit 1
    fi
    
    if docker-compose ps | grep -q "redis.*Up"; then
        echo -e "${GREEN}✓ Redis is running${NC}"
    else
        echo -e "${RED}❌ Redis failed to start${NC}"
        exit 1
    fi
elif command -v docker &> /dev/null; then
    echo "Docker found, but docker-compose not found. Trying 'docker compose'..."
    docker compose up -d postgres redis
    
    # Wait for services to be ready
    echo "Waiting for services to start (10 seconds)..."
    sleep 10
    
    # Check if services are running
    if docker compose ps | grep -q "postgres.*Up"; then
        echo -e "${GREEN}✓ PostgreSQL is running${NC}"
    else
        echo -e "${RED}❌ PostgreSQL failed to start${NC}"
        exit 1
    fi
    
    if docker compose ps | grep -q "redis.*Up"; then
        echo -e "${GREEN}✓ Redis is running${NC}"
    else
        echo -e "${RED}❌ Redis failed to start${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠ Docker not found${NC}"
    echo ""
    echo "Docker is not installed. You have two options:"
    echo ""
    echo "Option 1: Install Docker Desktop for Mac"
    echo "  Download from: https://www.docker.com/products/docker-desktop"
    echo "  Then run this script again"
    echo ""
    echo "Option 2: Use local PostgreSQL and Redis"
    echo "  Install via Homebrew:"
    echo "    brew install postgresql@14 redis"
    echo "    brew services start postgresql@14"
    echo "    brew services start redis"
    echo "  Then update backend/.env with local connection strings"
    echo ""
    echo "Continuing with setup (you'll need to set up databases manually)..."
fi

echo ""
echo "Step 3: Setting up database..."
echo "-------------------------------"

cd backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Run migrations
echo "Running database migrations..."
alembic upgrade head
echo -e "${GREEN}✓ Database migrations complete${NC}"

cd ..

echo ""
echo "Step 4: Installing frontend dependencies..."
echo "--------------------------------------------"

cd frontend

if [ ! -d "node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm install
    echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
else
    echo -e "${YELLOW}⚠ node_modules already exists, skipping${NC}"
fi

cd ..

echo ""
echo "================================================"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "================================================"
echo ""
echo "🎉 Your development environment is ready!"
echo ""
echo "Next steps:"
echo ""
echo "1. Start the backend (Terminal 1):"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   uvicorn main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "2. Start the frontend (Terminal 2):"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "3. (Optional) Start Celery worker (Terminal 3):"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   celery -A src.celery_app worker --loglevel=info"
echo ""
echo "4. Open your browser:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "5. Run the smoke test:"
echo "   See QUICKSTART.md for testing instructions"
echo ""
echo "📚 Documentation:"
echo "   - QUICKSTART.md - Quick start guide"
echo "   - QUICK_TEST_GUIDE.md - Testing guide"
echo "   - TROUBLESHOOTING.md - Common issues"
echo ""
