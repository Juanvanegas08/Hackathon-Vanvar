"""Simple async unit of work around AsyncSession."""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session_factory


class DatabaseUnitOfWork:
    """Context manager that owns a single AsyncSession lifecycle."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._external_session = session
        self.session: AsyncSession | None = None
        self._owns_session = False

    async def __aenter__(self) -> DatabaseUnitOfWork:
        if self._external_session is not None:
            self.session = self._external_session
            self._owns_session = False
            return self
        factory = get_session_factory()
        if factory is None:
            raise RuntimeError("Database is not configured (DATABASE_ENABLED=false)")
        self.session = factory()
        self._owns_session = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self.session is None:
            return
        try:
            if exc is not None:
                await self.session.rollback()
        finally:
            if self._owns_session:
                await self.session.close()
            self.session = None

    async def commit(self) -> None:
        if self.session is None:
            raise RuntimeError("Unit of work is not active")
        await self.session.commit()

    async def rollback(self) -> None:
        if self.session is None:
            raise RuntimeError("Unit of work is not active")
        await self.session.rollback()
