"""
Tests for authentication functionality.
"""
import pytest
from datetime import timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from src.utils.auth import AuthUtils
from src.models.database_models import Base, User
from src.database import get_db
from main import app


class TestPasswordHashing:
    """Test password hashing utilities"""
    
    def test_hash_password(self):
        """Test password hashing"""
        password = "TestPassword123"
        hashed = AuthUtils.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0
    
    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "TestPassword123"
        hashed = AuthUtils.hash_password(password)
        
        assert AuthUtils.verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "TestPassword123"
        wrong_password = "WrongPassword456"
        hashed = AuthUtils.hash_password(password)
        
        assert AuthUtils.verify_password(wrong_password, hashed) is False


class TestJWTTokens:
    """Test JWT token generation and validation"""
    
    def test_create_access_token(self):
        """Test access token creation"""
        data = {"sub": "test-user-id"}
        token = AuthUtils.create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_refresh_token(self):
        """Test refresh token creation"""
        data = {"sub": "test-user-id"}
        token = AuthUtils.create_refresh_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_decode_valid_token(self):
        """Test decoding a valid token"""
        data = {"sub": "test-user-id", "email": "test@example.com"}
        token = AuthUtils.create_access_token(data)
        
        decoded = AuthUtils.decode_token(token)
        
        assert decoded["sub"] == "test-user-id"
        assert decoded["email"] == "test@example.com"
        assert decoded["type"] == "access"
        assert "exp" in decoded
        assert "iat" in decoded
    
    def test_verify_token_type_access(self):
        """Test token type verification for access token"""
        data = {"sub": "test-user-id"}
        token = AuthUtils.create_access_token(data)
        payload = AuthUtils.decode_token(token)
        
        # Should not raise exception
        AuthUtils.verify_token_type(payload, "access")
    
    def test_verify_token_type_refresh(self):
        """Test token type verification for refresh token"""
        data = {"sub": "test-user-id"}
        token = AuthUtils.create_refresh_token(data)
        payload = AuthUtils.decode_token(token)
        
        # Should not raise exception
        AuthUtils.verify_token_type(payload, "refresh")
    
    def test_verify_token_type_mismatch(self):
        """Test token type verification with wrong type"""
        from fastapi import HTTPException
        
        data = {"sub": "test-user-id"}
        token = AuthUtils.create_access_token(data)
        payload = AuthUtils.decode_token(token)
        
        # Should raise exception
        with pytest.raises(HTTPException) as exc_info:
            AuthUtils.verify_token_type(payload, "refresh")
        
        assert exc_info.value.status_code == 401



# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_engine():
    """Create a test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def test_db(test_engine):
    """Create a test database session"""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture
async def client(test_db):
    """Create a test client with database override"""
    async def override_get_db():
        yield test_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    try:
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestUserRegistration:
    """Test user registration endpoint"""
    
    async def test_register_success(self, client: AsyncClient):
        """Test successful user registration"""
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "TestPassword123"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
    
    async def test_register_duplicate_email(self, client: AsyncClient):
        """Test registration with duplicate email"""
        # Register first user
        await client.post(
            "/api/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "TestPassword123"
            }
        )
        
        # Try to register with same email
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "DifferentPassword456"
            }
        )
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()
    
    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email format"""
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "not-an-email",
                "password": "TestPassword123"
            }
        )
        
        assert response.status_code == 422
    
    async def test_register_weak_password(self, client: AsyncClient):
        """Test registration with weak password"""
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "weak"
            }
        )
        
        assert response.status_code == 422


@pytest.mark.asyncio
class TestUserLogin:
    """Test user login endpoint"""
    
    async def test_login_success(self, client: AsyncClient):
        """Test successful login with valid credentials"""
        # Register user first
        await client.post(
            "/api/auth/register",
            json={
                "email": "login@example.com",
                "password": "TestPassword123"
            }
        )
        
        # Login with correct credentials
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "login@example.com",
                "password": "TestPassword123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
    
    async def test_login_wrong_password(self, client: AsyncClient):
        """Test login with incorrect password"""
        # Register user first
        await client.post(
            "/api/auth/register",
            json={
                "email": "wrongpass@example.com",
                "password": "CorrectPassword123"
            }
        )
        
        # Login with wrong password
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "wrongpass@example.com",
                "password": "WrongPassword456"
            }
        )
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()
    
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with non-existent email"""
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "TestPassword123"
            }
        )
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()
    
    async def test_login_invalid_email_format(self, client: AsyncClient):
        """Test login with invalid email format"""
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "not-an-email",
                "password": "TestPassword123"
            }
        )
        
        assert response.status_code == 422


@pytest.mark.asyncio
class TestTokenRefresh:
    """Test token refresh endpoint"""
    
    async def test_refresh_token_success(self, client: AsyncClient):
        """Test successful token refresh"""
        # Register and get tokens
        register_response = await client.post(
            "/api/auth/register",
            json={
                "email": "refresh@example.com",
                "password": "TestPassword123"
            }
        )
        
        refresh_token = register_response.json()["refresh_token"]
        
        # Refresh the token
        response = await client.post(
            "/api/auth/refresh",
            json={
                "refresh_token": refresh_token
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
        
        # New tokens should be different from original
        assert data["access_token"] != register_response.json()["access_token"]
        assert data["refresh_token"] != refresh_token
    
    async def test_refresh_with_invalid_token(self, client: AsyncClient):
        """Test refresh with invalid token"""
        response = await client.post(
            "/api/auth/refresh",
            json={
                "refresh_token": "invalid.token.here"
            }
        )
        
        assert response.status_code == 401
    
    async def test_refresh_with_access_token(self, client: AsyncClient):
        """Test refresh endpoint rejects access tokens"""
        # Register and get tokens
        register_response = await client.post(
            "/api/auth/register",
            json={
                "email": "wrongtoken@example.com",
                "password": "TestPassword123"
            }
        )
        
        access_token = register_response.json()["access_token"]
        
        # Try to use access token for refresh
        response = await client.post(
            "/api/auth/refresh",
            json={
                "refresh_token": access_token
            }
        )
        
        assert response.status_code == 401
        assert "token type" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestAuthenticatedEndpoints:
    """Test endpoints that require authentication"""
    
    async def test_get_current_user_success(self, client: AsyncClient):
        """Test getting current user info with valid token"""
        # Register user
        register_response = await client.post(
            "/api/auth/register",
            json={
                "email": "currentuser@example.com",
                "password": "TestPassword123"
            }
        )
        
        access_token = register_response.json()["access_token"]
        
        # Get current user info
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "currentuser@example.com"
        assert "id" in data
        assert "created_at" in data
        assert "notification_preferences" in data
    
    async def test_get_current_user_no_token(self, client: AsyncClient):
        """Test getting current user without token"""
        response = await client.get("/api/auth/me")
        
        assert response.status_code == 403
    
    async def test_get_current_user_invalid_token(self, client: AsyncClient):
        """Test getting current user with invalid token"""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        
        assert response.status_code == 401
