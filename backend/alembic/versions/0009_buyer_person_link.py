"""0009 link normalized buyers to synthetic persons.

Revision ID: 0009_buyer_person_link
Revises: 0008_analytics_views
Create Date: 2026-07-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from app.db.schemas import IDENTITY_SCHEMA, INGESTION_SCHEMA
from sqlalchemy.dialects import postgresql

revision: str = "0009_buyer_person_link"
down_revision: str | None = "0008_analytics_views"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "normalized_buyer_records",
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema=INGESTION_SCHEMA,
    )
    op.create_index(
        "ix_ingestion_normalized_buyer_records_person_id",
        "normalized_buyer_records",
        ["person_id"],
        schema=INGESTION_SCHEMA,
    )
    op.create_foreign_key(
        "fk_ingestion_normalized_buyer_records_person_id",
        "normalized_buyer_records",
        "persons",
        ["person_id"],
        ["id"],
        source_schema=INGESTION_SCHEMA,
        referent_schema=IDENTITY_SCHEMA,
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_ingestion_normalized_buyer_records_person_id",
        "normalized_buyer_records",
        schema=INGESTION_SCHEMA,
        type_="foreignkey",
    )
    op.drop_index(
        "ix_ingestion_normalized_buyer_records_person_id",
        table_name="normalized_buyer_records",
        schema=INGESTION_SCHEMA,
    )
    op.drop_column(
        "normalized_buyer_records",
        "person_id",
        schema=INGESTION_SCHEMA,
    )
