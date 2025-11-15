# Twitter Platform Enum Fix

## Problem

The database enum `platformenum` had mixed case values:
- Original values: `TIKTOK`, `YOUTUBE`, `INSTAGRAM`, `FACEBOOK` (UPPERCASE)
- Twitter was added as: `twitter` (lowercase)

This caused a mismatch between:
1. Database enum values (UPPERCASE)
2. Python enum values (were lowercase)
3. Platform adapter keys (lowercase)

## Solution

### 1. Database Migration (008)

Created migration `008_fix_platform_enum_casing.py` to:
- Update any existing `twitter` records to `TWITTER`
- Standardize on UPPERCASE enum values in the database

### 2. Python Enum Update

Updated `backend/src/models/database_models.py`:
```python
class PlatformEnum(str, enum.Enum):
    TIKTOK = "TIKTOK"      # Changed from "tiktok"
    YOUTUBE = "YOUTUBE"    # Changed from "youtube"
    TWITTER = "TWITTER"    # Changed from "twitter"
    INSTAGRAM = "INSTAGRAM"  # Changed from "instagram"
    FACEBOOK = "FACEBOOK"  # Changed from "facebook"
```

### 3. API Layer Updates

Updated `backend/src/api/platforms.py`:

**OAuth Callback** (line 249):
```python
# Convert platform string to enum (uppercase to match database)
platform_enum = PlatformEnum(platform.upper())
```

**Connected Platforms Endpoint** (line 369):
```python
platforms.append({
    "platform": conn.platform.value.lower(),  # Convert to lowercase for frontend
    ...
})
```

**Status Endpoint** (line 408):
```python
# Compare with uppercase since enum values are uppercase
connection = next((c for c in connections if c.platform.value.lower() == platform), None)
```

## Migration Steps

1. Run the migration:
```bash
cd backend
python3 -m alembic upgrade head
```

2. Restart the backend:
```bash
./stop.sh
./start.sh
```

## Verification

Check database enum values:
```sql
SELECT unnest(enum_range(NULL::platformenum));
```

Should show:
- TIKTOK
- YOUTUBE
- INSTAGRAM
- FACEBOOK
- TWITTER

(Note: lowercase `twitter` may still exist in the enum type but won't be used)

## Frontend Compatibility

The frontend enum remains lowercase for display purposes:
```typescript
export enum Platform {
  TIKTOK = 'tiktok',
  YOUTUBE = 'youtube',
  TWITTER = 'twitter',
  INSTAGRAM = 'instagram',
  FACEBOOK = 'facebook',
}
```

The API automatically converts between uppercase (database) and lowercase (frontend) formats.

## Files Changed

1. `backend/alembic/versions/008_fix_platform_enum_casing.py` - New migration
2. `backend/src/models/database_models.py` - Updated PlatformEnum values
3. `backend/src/api/platforms.py` - Added case conversion logic
