#!/usr/bin/env python3
"""Test Twitter OAuth 1.0a credentials"""

from src.config import get_settings
from requests_oauthlib import OAuth1Session

# Load from settings
settings = get_settings()
API_KEY = settings.twitter_api_key
API_SECRET = settings.twitter_api_secret
ACCESS_TOKEN = settings.twitter_access_token
ACCESS_TOKEN_SECRET = settings.twitter_access_token_secret

print("Testing Twitter OAuth 1.0a credentials...")
print(f"API Key: {API_KEY[:10]}...")
print(f"Access Token: {ACCESS_TOKEN[:20]}...")

# Create OAuth session
oauth = OAuth1Session(
    API_KEY,
    client_secret=API_SECRET,
    resource_owner_key=ACCESS_TOKEN,
    resource_owner_secret=ACCESS_TOKEN_SECRET
)

# Test with a simple API call
try:
    response = oauth.get("https://api.twitter.com/1.1/account/verify_credentials.json")
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ OAuth 1.0a credentials are VALID")
        print(f"   Authenticated as: @{data.get('screen_name')}")
    else:
        print(f"❌ OAuth 1.0a credentials are INVALID")
        print(f"   Response: {response.text}")
except Exception as e:
    print(f"❌ Error testing credentials: {e}")
