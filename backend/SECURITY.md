# Security Features

This document outlines the security features implemented in the Multi-Platform Video Scheduler backend.

## 1. Rate Limiting

### Implementation
- Uses SlowAPI (based on Flask-Limiter) for rate limiting
- Default limit: 100 requests per minute per user
- Uses Redis for distributed rate limiting across multiple instances
- Identifies users by JWT token (user ID) or falls back to IP address for unauthenticated requests

### Configuration
Rate limiting is configured in `src/middleware/rate_limiter.py` and can be adjusted via environment variables:

```bash
RATE_LIMIT_PER_MINUTE=100
```

### Response
When rate limit is exceeded, the API returns:
- Status Code: `429 Too Many Requests`
- Headers: `Retry-After` (seconds until limit resets)
- Body: Error message with rate limit details

### Custom Rate Limits
Individual endpoints can override the default rate limit using the `@limiter.limit()` decorator:

```python
from src.middleware import limiter

@router.post("/upload")
@limiter.limit("10/minute")  # Custom limit for this endpoint
async def upload_video(...):
    pass
```

## 2. Input Validation and Sanitization

### File Upload Validation
Implemented in `src/utils/validators.py`:

- **File Size Limit**: Maximum 500MB per file
- **File Type Validation**: 
  - Checks file extension (.mp4, .mov, .avi, .webm, .mkv)
  - Validates MIME type using python-magic (magic number detection)
  - Prevents malicious files disguised with video extensions
- **Filename Sanitization**: 
  - Removes path traversal characters (../, /, \)
  - Removes null bytes and control characters
  - Limits filename length to prevent buffer overflow attacks

### Text Input Sanitization
All text inputs are sanitized to prevent injection attacks:

- **Caption/Description**: 
  - Removes null bytes
  - Trims whitespace
  - Enforces maximum length limits
- **Tags**: 
  - Limited to 50 tags per video
  - Maximum 50 characters per tag
  - Removes empty tags
- **Hashtags**: 
  - Limited to 30 hashtags per post
  - Removes special characters except underscore
  - Strips # prefix if present
  - Maximum 100 characters per hashtag

### Pydantic Validation
All API endpoints use Pydantic models for request validation:
- Type checking
- Field constraints (min/max length, regex patterns)
- Required vs optional fields
- Automatic error responses for invalid data

## 3. Sensitive Data Protection

### Token Encryption (AES-256)
Platform OAuth tokens are encrypted at rest using AES-256 encryption:

- **Implementation**: `src/utils/encryption.py`
- **Algorithm**: Fernet (symmetric encryption with AES-256-CBC)
- **Key Derivation**: PBKDF2 with SHA-256 (100,000 iterations)
- **Storage**: Encrypted tokens stored in PostgreSQL database

#### Usage in Models
The `PlatformAuth` model automatically encrypts/decrypts tokens:

```python
# Storing tokens (automatic encryption)
platform_auth.set_access_token("raw_token_value")
platform_auth.set_refresh_token("raw_refresh_token")

# Retrieving tokens (automatic decryption)
access_token = platform_auth.get_access_token()
refresh_token = platform_auth.get_refresh_token()
```

### Environment Variables
All sensitive configuration is stored in environment variables:

- API keys and secrets
- Database credentials
- JWT signing keys
- Encryption keys
- SMTP credentials

**Never commit `.env` files to version control!**

### CORS Configuration
Cross-Origin Resource Sharing (CORS) is configured to only allow requests from trusted frontend domains:

```bash
# .env
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

In development:
```bash
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

### Password Hashing
User passwords are hashed using bcrypt with automatic salt generation:
- Implemented in `src/utils/auth.py`
- Uses passlib with bcrypt backend
- Automatic salt generation per password
- Configurable work factor (default: 12 rounds)

## 4. Authentication & Authorization

### JWT Tokens
- **Access Tokens**: Short-lived (15 minutes), used for API authentication
- **Refresh Tokens**: Long-lived (7 days), used to obtain new access tokens
- **Algorithm**: HS256 (HMAC with SHA-256)
- **Storage**: Client-side (localStorage or httpOnly cookies recommended)

### Row-Level Security
All database queries include user_id filters to ensure users can only access their own data:

```python
# Example: Users can only see their own videos
videos = await db.execute(
    select(Video).where(Video.user_id == current_user.id)
)
```

## 5. Additional Security Measures

### SQL Injection Prevention
- Uses SQLAlchemy ORM with parameterized queries
- No raw SQL queries with user input
- Input validation before database operations

### Error Handling
- Generic error messages to prevent information leakage
- Detailed errors logged server-side only
- No stack traces exposed to clients in production

### Logging
- Sensitive data (tokens, passwords) never logged
- Failed authentication attempts logged for monitoring
- Rate limit violations logged with user identifier

### HTTPS Enforcement
In production, always use HTTPS:
- Configure reverse proxy (nginx, Cloudflare) to enforce HTTPS
- Set secure cookie flags
- Use HSTS headers

## Security Checklist for Production

- [ ] Change all default secrets in `.env`
- [ ] Generate strong encryption key (32+ random bytes)
- [ ] Use strong JWT secret key (64+ random characters)
- [ ] Configure CORS for production domain only
- [ ] Enable HTTPS and HSTS
- [ ] Set up firewall rules (only allow necessary ports)
- [ ] Configure Redis authentication
- [ ] Use PostgreSQL SSL connections
- [ ] Set up automated security updates
- [ ] Enable Sentry or similar error tracking
- [ ] Configure rate limiting for production load
- [ ] Set up monitoring and alerting
- [ ] Regular security audits and dependency updates
- [ ] Implement backup and disaster recovery

## Generating Secure Keys

### Encryption Key
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### JWT Secret Key
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### Random Secret Key
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Reporting Security Issues

If you discover a security vulnerability, please email security@yourdomain.com instead of using the public issue tracker.

## Security Updates

- Regularly update dependencies: `pip install --upgrade -r requirements.txt`
- Monitor security advisories for Python packages
- Subscribe to security mailing lists for FastAPI, SQLAlchemy, etc.
- Use tools like `safety` to check for known vulnerabilities:
  ```bash
  pip install safety
  safety check
  ```
