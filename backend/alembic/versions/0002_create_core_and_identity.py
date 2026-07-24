"""0002 create core and identity.

Revision ID: 0002_core_identity
Revises: 0001_bootstrap
Create Date: 2026-07-23
"""

from __future__ import annotations

from collections.abc import Sequence

import app.db.models  # noqa: F401
from app.db.alembic_helpers import create_tables_for_schemas, drop_tables_for_schemas
from app.db.schemas import CORE_SCHEMA, IDENTITY_SCHEMA

revision: str = "0002_core_identity"
down_revision: str | None = "0001_bootstrap"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    create_tables_for_schemas((CORE_SCHEMA, IDENTITY_SCHEMA))


def downgrade() -> None:
    drop_tables_for_schemas((CORE_SCHEMA, IDENTITY_SCHEMA))
