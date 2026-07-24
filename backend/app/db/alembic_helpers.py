"""Shared helpers for schema-scoped Alembic migrations."""

from __future__ import annotations

from collections.abc import Iterable

from alembic import op
from sqlalchemy import Table, text

from app.db.base import Base


def tables_for_schemas(schemas: Iterable[str]) -> list[Table]:
    """Return metadata tables belonging to the given schemas, FK-safe order."""
    wanted = frozenset(schemas)
    return [table for table in Base.metadata.sorted_tables if table.schema in wanted]


def create_tables_for_schemas(schemas: Iterable[str]) -> None:
    """Create ORM tables for the given schemas without using create_all()."""
    bind = op.get_bind()
    for table in tables_for_schemas(schemas):
        table.create(bind, checkfirst=False)


def drop_tables_for_schemas(schemas: Iterable[str]) -> None:
    """Drop ORM tables for the given schemas in reverse dependency order."""
    bind = op.get_bind()
    for table in reversed(tables_for_schemas(schemas)):
        table.drop(bind, checkfirst=True)


def create_extension(name: str) -> None:
    """Create a PostgreSQL extension or raise a clear error."""
    try:
        op.execute(text(f'CREATE EXTENSION IF NOT EXISTS "{name}"'))
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"Failed to create required PostgreSQL extension '{name}'. "
            "Grant CREATE on the database or ask a DBA to install it."
        ) from exc


def drop_schema_if_empty(schema: str) -> None:
    """Drop a schema only when it contains no objects."""
    connection = op.get_bind()
    result = connection.execute(
        text(
            """
            SELECT COUNT(*) AS object_count
            FROM information_schema.tables
            WHERE table_schema = :schema
            """
        ),
        {"schema": schema},
    )
    count = int(result.scalar_one())
    if count == 0:
        op.execute(text(f'DROP SCHEMA IF EXISTS "{schema}"'))
