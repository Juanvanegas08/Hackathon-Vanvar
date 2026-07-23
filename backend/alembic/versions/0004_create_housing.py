"""0004 create housing.

Revision ID: 0004_housing
Revises: 0003_affiliation_leads
Create Date: 2026-07-23
"""

from __future__ import annotations

from collections.abc import Sequence

import app.db.models  # noqa: F401
from app.db.alembic_helpers import create_tables_for_schemas, drop_tables_for_schemas
from app.db.schemas import HOUSING_SCHEMA

revision: str = "0004_housing"
down_revision: str | None = "0003_affiliation_leads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    create_tables_for_schemas((HOUSING_SCHEMA,))


def downgrade() -> None:
    drop_tables_for_schemas((HOUSING_SCHEMA,))
