#!/bin/bash
# Quick Docker fix - stops everything and restarts Docker

echo "🔧 Quick Docker Fix..."
docker-compose down 2>/dev/null
pkill -9 -f Docker 2>/dev/null
sleep 3
open -a Docker
echo "⏳ Waiting for Docker to start (30 seconds)..."
sleep 30
if docker ps > /dev/null 2>&1; then
    echo "✅ Docker is running! Now run: ./start.sh"
else
    echo "⚠️  Docker may need more time. Wait a bit and run: docker ps"
fi
