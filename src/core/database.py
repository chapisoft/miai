"""
Async Database Session & Redis Connection Management.
"""

from typing import AsyncGenerator, Optional
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from core.config import settings
from core.telemetry import logger

Base = declarative_base()

# ── 1. PostgreSQL Async SQLAlchemy Engine ──────────────────────────────────
_async_engine = None
_async_session_factory = None


def get_async_engine():
    global _async_engine, _async_session_factory
    if _async_engine is None:
        try:
            _async_engine = create_async_engine(
                settings.async_database_url,
                pool_size=settings.POSTGRES_POOL_SIZE,
                max_overflow=settings.POSTGRES_MAX_OVERFLOW,
                pool_pre_ping=True,
                echo=settings.DEBUG
            )
            _async_session_factory = async_sessionmaker(
                bind=_async_engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False
            )
            logger.info("Initialized PostgreSQL Async Engine", extra={"host": settings.POSTGRES_HOST})
        except Exception as e:
            logger.warning("Could not initialize PostgreSQL engine immediately", extra={"error": str(e)})
    return _async_engine


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Dependency for database session."""
    engine = get_async_engine()
    if _async_session_factory is None:
        yield None  # Fallback for environments without running DB
        return

    async with _async_session_factory() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


# ── 2. Redis Async Client ──────────────────────────────────────────────────
_redis_client: Optional[aioredis.Redis] = None


async def get_redis_client() -> aioredis.Redis:
    """Provides a singleton async Redis connection."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
    return _redis_client


async def close_database_connections():
    """Cleanly closes database and cache pools during application shutdown."""
    global _async_engine, _redis_client
    if _async_engine is not None:
        await _async_engine.dispose()
        logger.info("Disposed PostgreSQL connection pool")
    if _redis_client is not None:
        await _redis_client.close()
        logger.info("Closed Redis connection")
