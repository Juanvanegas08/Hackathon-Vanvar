"""Async session factory for CasaLista PostgreSQL access."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.engine import get_engine

AsyncSessionFactory: async_sessionmaker[AsyncSession] | None = None


def get_session_factory() -> async_sessionmaker[AsyncSession] | None:
    """Return the session factory when an engine is available."""
    global AsyncSessionFactory
    if AsyncSessionFactory is not None:
        return AsyncSessionFactory
    engine = get_engine()
    if engine is None:
        return None
    AsyncSessionFactory = async_sessionmaker(
        engine,
        expire_on_commit=False,
        autoflush=False,
        class_=AsyncSession,
    )
    return AsyncSessionFactory


def reset_session_factory() -> None:
    """Clear the cached session factory (intended for tests)."""
    global AsyncSessionFactory
    AsyncSessionFactory = None


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Open a short-lived AsyncSession and close it afterwards."""
    factory = get_session_factory()
    if factory is None:
        raise RuntimeError("Database is not configured (DATABASE_ENABLED=false)")
    session = factory()
    try:
        yield session
    finally:
        await session.close()
