"""Database health-check service."""

from __future__ import annotations

import asyncio
import selectors
import sys
import time
from typing import Any
from urllib.parse import urlparse

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.core.config import Settings, get_settings, redact_database_url
from app.db.schemas import APPLICATION_SCHEMAS, REQUIRED_EXTENSIONS


def _redacted_database_name(url: str) -> str:
    path = urlparse(url).path.lstrip("/")
    name = path.split("/")[0] if path else ""
    if len(name) <= 4:
        return "***"
    return f"{name[:2]}***{name[-2:]}"


def _expected_head_revisions() -> list[str]:
    cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(cfg)
    return list(script.get_heads())


async def _fetch_scalar(connection: AsyncConnection, sql: str, **params: Any) -> Any:
    result = await connection.execute(text(sql), params)
    return result.scalar()


def _windows_selector_loop() -> asyncio.AbstractEventLoop:
    return asyncio.SelectorEventLoop(selectors.SelectSelector())


async def check_database_health(settings: Settings | None = None) -> dict[str, Any]:
    """Return a redacted database health payload."""
    cfg = settings or get_settings()
    if not cfg.is_database_configured:
        return {
            "status": "degraded",
            "database": {
                "connected": False,
                "reason": "database_not_configured",
            },
        }

    url = cfg.get_database_url()
    assert url is not None

    engine = create_async_engine(url, pool_pre_ping=True)
    started = time.perf_counter()
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
            latency_ms = round((time.perf_counter() - started) * 1000)

            version = await _fetch_scalar(connection, "SHOW server_version")

            current_revision = None
            try:
                current_revision = await _fetch_scalar(
                    connection,
                    "SELECT version_num FROM core.alembic_version LIMIT 1",
                )
            except Exception:  # noqa: BLE001
                current_revision = None

            schema_rows = await connection.execute(
                text(
                    """
                    SELECT nspname
                    FROM pg_namespace
                    WHERE nspname = ANY(:schemas)
                    """
                ),
                {"schemas": list(APPLICATION_SCHEMAS)},
            )
            available_schemas = {row[0] for row in schema_rows}
            schemas_available = set(APPLICATION_SCHEMAS).issubset(available_schemas)

            extension_rows = await connection.execute(
                text(
                    """
                    SELECT extname
                    FROM pg_extension
                    WHERE extname = ANY(:extensions)
                    """
                ),
                {"extensions": list(REQUIRED_EXTENSIONS)},
            )
            available_extensions = {row[0] for row in extension_rows}
            extensions_available = set(REQUIRED_EXTENSIONS).issubset(
                available_extensions
            )

        heads = _expected_head_revisions()
        if current_revision is None:
            migration_status = "not_initialized"
        elif current_revision in heads:
            migration_status = "up_to_date"
        else:
            migration_status = "pending"

        status = "ok"
        if (
            migration_status != "up_to_date"
            or not schemas_available
            or not extensions_available
        ):
            status = "degraded"

        payload: dict[str, Any] = {
            "status": status,
            "database": {
                "connected": True,
                "migration_status": migration_status,
                "current_revision": current_revision,
                "expected_heads": heads,
                "schemas_available": schemas_available,
                "extensions_available": extensions_available,
                "latency_ms": latency_ms,
                "postgres_version": str(version),
                "database_name_redacted": _redacted_database_name(url),
            },
        }
        if cfg.app_env.lower() != "production":
            payload["database"]["url_redacted"] = redact_database_url(url)
        return payload
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "degraded",
            "database": {
                "connected": False,
                "reason": "connection_failed",
                "error_type": type(exc).__name__,
            },
        }
    finally:
        await engine.dispose()


def run_database_health_sync(settings: Settings | None = None) -> dict[str, Any]:
    """Synchronous helper for scripts (Windows-safe)."""
    if sys.platform.startswith("win"):
        loop = _windows_selector_loop()
        try:
            return loop.run_until_complete(check_database_health(settings))
        finally:
            loop.close()
    return asyncio.run(check_database_health(settings))
