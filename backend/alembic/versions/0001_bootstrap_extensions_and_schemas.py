"""0001 bootstrap extensions and schemas.

Revision ID: 0001_bootstrap
Revises:
Create Date: 2026-07-23
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from app.db.alembic_helpers import create_extension, drop_schema_if_empty
from app.db.schemas import APPLICATION_SCHEMAS, REQUIRED_EXTENSIONS
from sqlalchemy import text

revision: str = "0001_bootstrap"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for extension in REQUIRED_EXTENSIONS:
        create_extension(extension)

    for schema in APPLICATION_SCHEMAS:
        op.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))


def downgrade() -> None:
    for schema in reversed(APPLICATION_SCHEMAS):
        drop_schema_if_empty(schema)
    # Extensions are intentionally retained (may be shared).
