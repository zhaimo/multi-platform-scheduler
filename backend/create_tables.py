#!/usr/bin/env python3
"""
Simple script to create database tables directly using SQLAlchemy
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from src.models.database_models import Base
from src.config import settings

async def create_tables():
    """Create all database tables"""
    print(f"Connecting to database: {settings.database_url}")
    
    engine = create_async_engine(settings.database_url, echo=True)
    
    async with engine.begin() as conn:
        print("Dropping all tables...")
        await conn.run_sync(Base.metadata.drop_all)
        
        print("Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)
    
    await engine.dispose()
    print("✅ All tables created successfully!")

if __name__ == "__main__":
    asyncio.run(create_tables())
