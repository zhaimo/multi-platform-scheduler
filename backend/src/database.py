"""Database connection and session management"""

from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager, contextmanager

from src.config import get_settings

# Global engine and session factory
_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None
_sync_engine: Engine | None = None
_sync_session_factory: sessionmaker[Session] | None = None


def get_engine() -> AsyncEngine:
    """Get or create the database engine"""
    global _engine
    
    if _engine is None:
        settings = get_settings()
        
        # Convert postgresql:// to postgresql+asyncpg://
        database_url = settings.database_url
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif not database_url.startswith("postgresql+asyncpg://"):
            database_url = f"postgresql+asyncpg://{database_url}"
        
        _engine = create_async_engine(
            database_url,
            echo=settings.debug,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,  # Verify connections before using
        )
    
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the async session factory"""
    global _async_session_factory
    
    if _async_session_factory is None:
        engine = get_engine()
        _async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    
    return _async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes to get database session.
    
    Usage:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database session outside of FastAPI routes.
    
    Usage:
        async with get_db_context() as db:
            result = await db.execute(select(User))
            users = result.scalars().all()
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database connection.
    Call this on application startup.
    """
    # Just initialize the engine and session factory
    get_engine()
    get_session_factory()


async def close_db() -> None:
    """
    Close database connections.
    Call this on application shutdown.
    """
    global _engine, _async_session_factory
    
    if _engine is not None:
        await _engine.dispose()
        _engine = None
    
    _async_session_factory = None


# For testing purposes - create engine with different settings
def create_test_engine(database_url: str) -> AsyncEngine:
    """Create a test database engine"""
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    return create_async_engine(
        database_url,
        echo=False,
        poolclass=NullPool,  # Don't pool connections in tests
    )


def create_test_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create a test session factory"""
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


# Synchronous database session for Celery tasks
def get_sync_engine() -> Engine:
    """Get or create the synchronous database engine for Celery tasks"""
    global _sync_engine
    
    if _sync_engine is None:
        settings = get_settings()
        
        # Use psycopg2 for sync connections
        database_url = settings.database_url
        if database_url.startswith("postgresql+asyncpg://"):
            database_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        elif not database_url.startswith("postgresql://"):
            database_url = f"postgresql://{database_url}"
        
        _sync_engine = create_engine(
            database_url,
            echo=settings.debug,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,
        )
    
    return _sync_engine


def get_sync_session_factory() -> sessionmaker[Session]:
    """Get or create the synchronous session factory for Celery tasks"""
    global _sync_session_factory
    
    if _sync_session_factory is None:
        engine = get_sync_engine()
        _sync_session_factory = sessionmaker(
            engine,
            class_=Session,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    
    return _sync_session_factory


@contextmanager
def get_sync_db() -> Generator[Session, None, None]:
    """
    Context manager for synchronous database session (for Celery tasks).
    
    Usage:
        with get_sync_db() as db:
            result = db.execute(select(User))
            users = result.scalars().all()
    """
    session_factory = get_sync_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
