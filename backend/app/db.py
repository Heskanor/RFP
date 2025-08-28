"""
Database configuration and connection management for RFP Buyer
"""
import os
import logging
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    """Base class for SQLAlchemy models"""
    pass

class DatabaseManager:
    """Database connection manager"""
    
    def __init__(self):
        self.engine = None
        self.async_session_factory = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize database connections"""
        if self._initialized:
            return
            
        db_url = os.getenv("SUPABASE_DB_URL")
        if not db_url:
            raise ValueError("SUPABASE_DB_URL environment variable is required")
        
        # Convert postgresql:// to postgresql+asyncpg:// for async
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif not db_url.startswith("postgresql+asyncpg://"):
            raise ValueError("Database URL must use postgresql:// or postgresql+asyncpg:// scheme")
        
        logger.info(f"Connecting to database: {db_url.split('@')[1] if '@' in db_url else 'localhost'}")
        
        # Create async engine
        self.engine = create_async_engine(
            db_url,
            echo=os.getenv("DEBUG", "false").lower() == "true",
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        
        # Create session factory
        self.async_session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Test connection and initialize pgvector if needed
        await self._test_connection()
        await self._initialize_extensions()
        
        self._initialized = True
        logger.info("✅ Database initialized successfully")
        
    async def _test_connection(self):
        """Test database connection"""
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
                logger.info("✅ Database connection test passed")
        except Exception as e:
            logger.error(f"❌ Database connection test failed: {e}")
            raise
    
    async def _initialize_extensions(self):
        """Initialize required PostgreSQL extensions"""
        try:
            async with self.engine.begin() as conn:
                # Enable pgcrypto for gen_random_uuid()
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto;"))
                logger.info("✅ pgcrypto extension enabled")
                
                # Enable pgvector for vector operations
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                logger.info("✅ pgvector extension enabled")
                
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize extensions: {e}")
            # Don't fail if extensions can't be created (user might not have permissions)
        
    async def close(self):
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
            logger.info("✅ Database connections closed")
        self._initialized = False

    @asynccontextmanager
    async def get_session(self):
        """Get async database session with automatic cleanup"""
        if not self._initialized:
            await self.initialize()
            
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

# Global database manager
db_manager = DatabaseManager()

async def initialize_database():
    """Initialize database connections"""
    await db_manager.initialize()

async def close_database():
    """Close database connections"""
    await db_manager.close()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for FastAPI dependency injection"""
    if not db_manager._initialized:
        await db_manager.initialize()
        
    async with db_manager.async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def execute_query(query: str, params: Optional[dict] = None):
    """Execute raw SQL query"""
    async with db_manager.get_session() as session:
        result = await session.execute(text(query), params or {})
        return result.fetchall()

async def execute_command(command: str, params: Optional[dict] = None):
    """Execute SQL command (INSERT, UPDATE, DELETE)"""
    async with db_manager.get_session() as session:
        result = await session.execute(text(command), params or {})
        return result.rowcount

# Utility function to check if database is ready
async def health_check() -> bool:
    """Check if database is healthy"""
    try:
        await execute_query("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False

