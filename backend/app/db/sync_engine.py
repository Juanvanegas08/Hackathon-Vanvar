"""Sync SQLAlchemy engine/session for repositories used by sync services."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings

_sync_engine: Engine | None = None
_sync_session_factory: sessionmaker[Session] | None = None


def create_sync_engine(settings: Settings | None = None) -> Engine | None:
    cfg = settings or get_settings()
    if not cfg.is_database_configured:
        return None
    url = cfg.get_database_url()
    if url is None:
        return None
    return create_engine(
        url,
        echo=cfg.database_echo,
        pool_pre_ping=True,
        pool_size=cfg.database_pool_size,
        max_overflow=cfg.database_max_overflow,
        pool_timeout=cfg.database_pool_timeout_seconds,
        pool_recycle=cfg.database_pool_recycle_seconds,
    )


def get_sync_engine(settings: Settings | None = None) -> Engine | None:
    global _sync_engine
    if _sync_engine is not None:
        return _sync_engine
    _sync_engine = create_sync_engine(settings)
    return _sync_engine


def get_sync_session_factory(
    settings: Settings | None = None,
) -> sessionmaker[Session] | None:
    global _sync_session_factory
    if _sync_session_factory is not None:
        return _sync_session_factory
    engine = get_sync_engine(settings)
    if engine is None:
        return None
    _sync_session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    return _sync_session_factory


def reset_sync_engine() -> None:
    global _sync_engine, _sync_session_factory
    if _sync_engine is not None:
        _sync_engine.dispose()
    _sync_engine = None
    _sync_session_factory = None


@contextmanager
def sync_session_scope(settings: Settings | None = None) -> Iterator[Session]:
    factory = get_sync_session_factory(settings)
    if factory is None:
        raise RuntimeError("Database is not configured (DATABASE_ENABLED=false)")
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
