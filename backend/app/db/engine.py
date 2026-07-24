"""Async SQLAlchemy engine factory.

The engine is created lazily and only when DATABASE_ENABLED is true.
Importing this module must not open database connections.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import Settings, get_settings

_engine: AsyncEngine | None = None


def create_engine(settings: Settings | None = None) -> AsyncEngine | None:
    """Create an AsyncEngine when the database is configured.

    Returns None when DATABASE_ENABLED is false or DATABASE_URL is missing.
    """
    cfg = settings or get_settings()
    if not cfg.is_database_configured:
        return None
    url = cfg.get_database_url()
    if url is None:
        return None
    return create_async_engine(
        url,
        echo=cfg.database_echo,
        pool_pre_ping=True,
        pool_size=cfg.database_pool_size,
        max_overflow=cfg.database_max_overflow,
        pool_timeout=cfg.database_pool_timeout_seconds,
        pool_recycle=cfg.database_pool_recycle_seconds,
    )


def get_engine() -> AsyncEngine | None:
    """Return the process-wide engine, creating it once when needed."""
    global _engine
    if _engine is not None:
        return _engine
    _engine = create_engine()
    return _engine


def reset_engine() -> None:
    """Clear the cached engine (intended for tests)."""
    global _engine
    _engine = None
