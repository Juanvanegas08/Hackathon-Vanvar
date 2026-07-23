"""Alembic environment with async PostgreSQL support."""

from __future__ import annotations

import asyncio
import selectors
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Ensure backend root is importable when running from other CWDs.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import app.db.models  # noqa: E402, F401
from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.schemas import APPLICATION_SCHEMAS, SYSTEM_SCHEMAS  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

APPLICATION_SCHEMA_SET = frozenset(APPLICATION_SCHEMAS)


def get_database_url() -> str:
    """Load DATABASE_URL from settings and escape % for ConfigParser."""
    settings = get_settings()
    url = settings.get_database_url()
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not configured. Set it in backend/.env before running Alembic."
        )
    # ConfigParser treats % as interpolation; escape for alembic.ini safety.
    return url.replace("%", "%%")


def include_name(name: str | None, type_: str, parent_names: dict[str, str | None]) -> bool:
    """Limit Alembic inspection to CasaLista application schemas."""
    if type_ == "schema":
        return name in APPLICATION_SCHEMA_SET
    if type_ == "table":
        schema = parent_names.get("schema_name")
        if schema in SYSTEM_SCHEMAS:
            return False
        if schema is None:
            return False
        return schema in APPLICATION_SCHEMA_SET
    return True


def include_object(
    object_: object,
    name: str | None,
    type_: str,
    reflected: bool,
    compare_to: object | None,
) -> bool:
    """Exclude views and non-application objects from autogenerate."""
    del reflected, compare_to
    if type_ == "table":
        schema = getattr(object_, "schema", None)
        if schema in SYSTEM_SCHEMAS or schema not in APPLICATION_SCHEMA_SET:
            return False
        info = getattr(object_, "info", {}) or {}
        if info.get("is_view"):
            return False
    if type_ == "schema":
        return name in APPLICATION_SCHEMA_SET
    return True


def configure_context(*, connection: Connection | None = None) -> None:
    """Shared Alembic context configuration."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_database_url()

    if connection is not None:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_name=include_name,
            include_object=include_object,
            compare_type=True,
            compare_server_default=True,
            version_table_schema="core",
            version_table="alembic_version",
            # Create version table in core after schemas exist.
            render_as_batch=False,
        )
    else:
        context.configure(
            url=get_database_url().replace("%%", "%"),
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
            include_schemas=True,
            include_name=include_name,
            include_object=include_object,
            compare_type=True,
            compare_server_default=True,
            version_table_schema="core",
            version_table="alembic_version",
        )


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""
    configure_context()
    with context.begin_transaction():
        context.run_migrations()


def ensure_core_schema(connection: Connection) -> None:
    """Ensure core exists so Alembic can store alembic_version there."""
    connection.execute(text('CREATE SCHEMA IF NOT EXISTS "core"'))
    connection.commit()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with an established connection."""
    ensure_core_schema(connection)
    configure_context(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine and NullPool."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def _windows_selector_loop() -> asyncio.AbstractEventLoop:
    """Psycopg async requires SelectorEventLoop on Windows."""
    return asyncio.SelectorEventLoop(selectors.SelectSelector())


def run_migrations_online() -> None:
    """Run migrations in online async mode."""
    if sys.platform.startswith("win"):
        asyncio.run(run_async_migrations(), loop_factory=_windows_selector_loop)
    else:
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
