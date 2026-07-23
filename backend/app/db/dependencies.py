"""FastAPI dependencies for database sessions."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield an AsyncSession for a request.

    Commits are the responsibility of services / units of work.
    On exception the session is rolled back; it is always closed.
    """
    factory = get_session_factory()
    if factory is None:
        raise RuntimeError("Database is not configured (DATABASE_ENABLED=false)")
    session = factory()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
