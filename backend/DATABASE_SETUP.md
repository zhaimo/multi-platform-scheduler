# Database Setup Guide

This document explains the database models and setup for the Multi-Platform Video Scheduler.

## Overview

The application uses PostgreSQL with SQLAlchemy ORM and Alembic for migrations. All database operations are asynchronous using `asyncpg`.

## Models

### Core Models

1. **User** - User accounts with authentication
2. **Video** - Uploaded videos with metadata
3. **PlatformAuth** - OAuth tokens for social media platforms (encrypted)
4. **Post** - Individual posts to platforms
5. **MultiPost** - Groups of posts across multiple platforms
6. **Schedule** - Scheduled and recurring posts
7. **PostTemplate** - Reusable post configurations
8. **VideoAnalytics** - Performance metrics from platforms

### Key Features

- **UUID Primary Keys** - All tables use UUIDs for better distribution
- **Indexes** - Optimized for common queries (user_id, video_id, platform, status)
- **Encryption** - Platform tokens are encrypted using Fernet (AES-256)
- **Relationships** - Proper foreign keys with cascade deletes
- **Enums** - Type-safe platform and status enums

## Database Connection

### Async Session Management

```python
from src.database import get_db
from fastapi import Depends

@app.get("/videos")
async def get_videos(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Video))
    return result.scalars().all()
```

### Outside FastAPI Routes

```python
from src.database import get_db_context

async with get_db_context() as db:
    result = await db.execute(select(User))
    users = result.scalars().all()
```

## Migrations

### Setup

Alembic is configured and ready to use. The initial migration creates all tables.

### Running Migrations

```bash
# Apply migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Description"

# Rollback
alembic downgrade -1
```

## Environment Variables

Required environment variables:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/video_scheduler
ENCRYPTION_KEY=<base64-encoded-32-byte-key>
```

### Generate Encryption Key

```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(key.decode())  # Use this in ENCRYPTION_KEY
```

## Token Encryption

Platform OAuth tokens are automatically encrypted:

```python
# Storing tokens
platform_auth = PlatformAuth(user_id=user_id, platform="tiktok")
platform_auth.set_access_token("raw_token_here")
platform_auth.set_refresh_token("raw_refresh_token")

# Retrieving tokens
access_token = platform_auth.get_access_token()
refresh_token = platform_auth.get_refresh_token()
```

## Application Lifecycle

```python
from src.database import init_db, close_db

# On startup
await init_db()

# On shutdown
await close_db()
```

## Testing

For tests, use the test utilities:

```python
from src.database import create_test_engine, create_test_session_factory

engine = create_test_engine("postgresql://test:test@localhost/test_db")
session_factory = create_test_session_factory(engine)
```
