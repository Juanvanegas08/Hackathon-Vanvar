"""0003 create affiliation and leads.

Revision ID: 0003_affiliation_leads
Revises: 0002_core_identity
Create Date: 2026-07-23
"""

from __future__ import annotations

from collections.abc import Sequence

import app.db.models  # noqa: F401
from app.db.alembic_helpers import create_tables_for_schemas, drop_tables_for_schemas
from app.db.schemas import AFFILIATION_SCHEMA, LEADS_SCHEMA

revision: str = "0003_affiliation_leads"
down_revision: str | None = "0002_core_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    create_tables_for_schemas((AFFILIATION_SCHEMA, LEADS_SCHEMA))


def downgrade() -> None:
    drop_tables_for_schemas((AFFILIATION_SCHEMA, LEADS_SCHEMA))
