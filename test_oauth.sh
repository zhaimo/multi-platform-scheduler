#!/bin/bash

# Test OAuth endpoints
# First, login to get a token

echo "Testing OAuth endpoints..."
echo ""

# Get JWT token (replace with your actual credentials)
echo "1. Login to get JWT token..."
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to get token. Make sure you have a test user."
  exit 1
fi

echo "✅ Got token: ${TOKEN:0:20}..."
echo ""

# Test /connected endpoint
echo "2. Testing GET /api/auth/platforms/connected..."
curl -s -X GET http://localhost:8000/api/auth/platforms/connected \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool
echo ""

# Test /youtube/authorize endpoint
echo "3. Testing GET /api/auth/platforms/youtube/authorize..."
RESPONSE=$(curl -s -X GET http://localhost:8000/api/auth/platforms/youtube/authorize \
  -H "Authorization: Bearer $TOKEN")

echo "$RESPONSE" | python3 -m json.tool
echo ""

# Extract authorization URL
AUTH_URL=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('authorization_url', ''))" 2>/dev/null)

if [ -n "$AUTH_URL" ]; then
  echo "✅ Authorization URL generated successfully!"
  echo "URL: $AUTH_URL"
  echo ""
  echo "To test the full flow:"
  echo "1. Open this URL in your browser: $AUTH_URL"
  echo "2. Grant permissions"
  echo "3. You'll be redirected back to the app"
else
  echo "❌ Failed to get authorization URL"
fi
