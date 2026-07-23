"""0007 create ingestion and audit.

Revision ID: 0007_ingestion_audit
Revises: 0006_conversations_commercial
Create Date: 2026-07-23
"""

from __future__ import annotations

from collections.abc import Sequence

import app.db.models  # noqa: F401
from alembic import op
from app.db.alembic_helpers import create_tables_for_schemas, drop_tables_for_schemas
from app.db.schemas import AUDIT_SCHEMA, HOUSING_SCHEMA, INGESTION_SCHEMA

revision: str = "0007_ingestion_audit"
down_revision: str | None = "0006_conversations_commercial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    create_tables_for_schemas((INGESTION_SCHEMA, AUDIT_SCHEMA))
    op.create_foreign_key(
        "fk_housing_hist_profiles_batch_id",
        "project_historical_profiles",
        "import_batches",
        ["source_batch_id"],
        ["id"],
        source_schema=HOUSING_SCHEMA,
        referent_schema=INGESTION_SCHEMA,
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_housing_hist_profiles_batch_id",
        "project_historical_profiles",
        schema=HOUSING_SCHEMA,
        type_="foreignkey",
    )
    drop_tables_for_schemas((INGESTION_SCHEMA, AUDIT_SCHEMA))
