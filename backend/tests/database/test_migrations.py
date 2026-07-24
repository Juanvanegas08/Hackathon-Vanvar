"""Integration tests for Alembic migrations.

Destructive tests run only when TEST_DATABASE_URL is configured.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from app.db.schemas import APPLICATION_SCHEMAS, REQUIRED_EXTENSIONS
from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _test_database_url() -> str | None:
    return os.getenv("TEST_DATABASE_URL") or None


pytestmark = pytest.mark.skipif(
    not _test_database_url(),
    reason="TEST_DATABASE_URL is not configured; skipping destructive migration tests",
)


def _sync_url(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def _run_alembic(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    # Ensure Alembic uses TEST_DATABASE_URL via temporary DATABASE_URL override.
    test_url = _test_database_url()
    assert test_url is not None
    env["DATABASE_URL"] = test_url
    env["DATABASE_ENABLED"] = "true"
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="module")
def migrated_database() -> None:
    result = _run_alembic("upgrade", "head")
    if result.returncode != 0:
        pytest.fail(f"alembic upgrade failed:\n{result.stdout}\n{result.stderr}")
    yield
    # Leave database at head for reuse; full downgrade covered in dedicated test.


def test_upgrade_creates_schemas_extensions_and_version(migrated_database: None) -> None:
    url = _test_database_url()
    assert url is not None
    engine = create_engine(_sync_url(url))
    try:
        with engine.connect() as connection:
            schemas = {
                row[0]
                for row in connection.execute(
                    text(
                        "SELECT schema_name FROM information_schema.schemata "
                        "WHERE schema_name = ANY(:schemas)"
                    ),
                    {"schemas": list(APPLICATION_SCHEMAS)},
                )
            }
            assert set(APPLICATION_SCHEMAS).issubset(schemas)

            extensions = {
                row[0]
                for row in connection.execute(
                    text(
                        "SELECT extname FROM pg_extension WHERE extname = ANY(:exts)"
                    ),
                    {"exts": list(REQUIRED_EXTENSIONS)},
                )
            }
            assert set(REQUIRED_EXTENSIONS).issubset(extensions)

            revision = connection.execute(
                text("SELECT version_num FROM core.alembic_version LIMIT 1")
            ).scalar()
            assert revision == "0008_analytics_views"

            views = {
                row[0]
                for row in connection.execute(
                    text(
                        "SELECT table_name FROM information_schema.views "
                        "WHERE table_schema = 'analytics'"
                    )
                )
            }
            assert {
                "lead_funnel",
                "project_interest",
                "conversation_performance",
            }.issubset(views)
    finally:
        engine.dispose()


def test_downgrade_and_reupgrade_roundtrip() -> None:
    down = _run_alembic("downgrade", "base")
    if down.returncode != 0:
        pytest.fail(f"alembic downgrade failed:\n{down.stdout}\n{down.stderr}")

    url = _test_database_url()
    assert url is not None
    engine = create_engine(_sync_url(url))
    try:
        with engine.connect() as connection:
            remaining = connection.execute(
                text(
                    """
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = ANY(:schemas)
                      AND table_type = 'BASE TABLE'
                    """
                ),
                {"schemas": list(APPLICATION_SCHEMAS)},
            ).scalar()
            assert remaining == 0

            extensions = {
                row[0]
                for row in connection.execute(
                    text(
                        "SELECT extname FROM pg_extension WHERE extname = ANY(:exts)"
                    ),
                    {"exts": list(REQUIRED_EXTENSIONS)},
                )
            }
            # Extensions must survive downgrade.
            assert set(REQUIRED_EXTENSIONS).issubset(extensions)
    finally:
        engine.dispose()

    up = _run_alembic("upgrade", "head")
    if up.returncode != 0:
        pytest.fail(f"alembic re-upgrade failed:\n{up.stdout}\n{up.stderr}")
