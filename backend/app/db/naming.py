"""SQLAlchemy naming conventions for named constraints."""

from collections.abc import Callable
from typing import Any

from sqlalchemy import MetaData
from sqlalchemy.schema import Constraint, Table


def _schema_token(constraint: Constraint, table: Table) -> str:  # noqa: ARG001
    """Return a stable schema token for constraint names."""
    return table.schema or "public"


# Callable tokens are supported by SQLAlchemy MetaData naming conventions.
NAMING_CONVENTION: dict[str, str | Callable[..., str]] = {
    "ix": "ix_%(schema_token)s_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(schema_token)s_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(schema_token)s_%(table_name)s_%(constraint_name)s",
    "fk": (
        "fk_%(schema_token)s_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s"
    ),
    "pk": "pk_%(schema_token)s_%(table_name)s",
    "schema_token": _schema_token,
}


def create_metadata() -> MetaData:
    """Create MetaData with CasaLista naming conventions."""
    return MetaData(naming_convention=NAMING_CONVENTION)


def constraint_kwargs(**extra: Any) -> dict[str, Any]:
    """Helper to keep explicit constraint names in table args."""
    return extra
