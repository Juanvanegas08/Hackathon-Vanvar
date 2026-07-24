"""Health-check behavior when database is unavailable or disabled."""

from __future__ import annotations

import asyncio

from app.core.config import Settings
from app.services.database_health_service import check_database_health


def test_health_handles_database_not_configured() -> None:
    settings = Settings(DATABASE_ENABLED=False, DATABASE_URL=None)

    async def _run() -> dict[str, object]:
        return await check_database_health(settings)

    payload = asyncio.run(_run())
    assert payload["status"] == "degraded"
    database = payload["database"]
    assert isinstance(database, dict)
    assert database["connected"] is False
    assert database["reason"] == "database_not_configured"


def test_health_handles_connection_failure() -> None:
    settings = Settings(
        DATABASE_ENABLED=True,
        DATABASE_URL="postgresql+psycopg://user:pass@127.0.0.1:1/home_30x",
    )

    async def _run() -> dict[str, object]:
        return await check_database_health(settings)

    if __import__("sys").platform.startswith("win"):
        import selectors

        loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
        try:
            payload = loop.run_until_complete(_run())
        finally:
            loop.close()
    else:
        payload = asyncio.run(_run())

    assert payload["status"] == "degraded"
    database = payload["database"]
    assert isinstance(database, dict)
    assert database["connected"] is False
