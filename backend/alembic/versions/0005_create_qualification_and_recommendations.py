"""0005 create qualification and recommendations.

Revision ID: 0005_qual_recs
Revises: 0004_housing
Create Date: 2026-07-23
"""

from __future__ import annotations

from collections.abc import Sequence

import app.db.models  # noqa: F401
from app.db.alembic_helpers import create_tables_for_schemas, drop_tables_for_schemas
from app.db.schemas import QUALIFICATION_SCHEMA, RECOMMENDATIONS_SCHEMA

revision: str = "0005_qual_recs"
down_revision: str | None = "0004_housing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    create_tables_for_schemas((QUALIFICATION_SCHEMA, RECOMMENDATIONS_SCHEMA))


def downgrade() -> None:
    drop_tables_for_schemas((QUALIFICATION_SCHEMA, RECOMMENDATIONS_SCHEMA))
