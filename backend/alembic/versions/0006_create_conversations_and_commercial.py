"""0006 create conversations and commercial.

Revision ID: 0006_conversations_commercial
Revises: 0005_qual_recs
Create Date: 2026-07-23
"""

from __future__ import annotations

from collections.abc import Sequence

import app.db.models  # noqa: F401
from alembic import op
from app.db.alembic_helpers import create_tables_for_schemas, drop_tables_for_schemas
from app.db.schemas import COMMERCIAL_SCHEMA, CONVERSATIONS_SCHEMA, QUALIFICATION_SCHEMA

revision: str = "0006_conversations_commercial"
down_revision: str | None = "0005_qual_recs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    create_tables_for_schemas((CONVERSATIONS_SCHEMA, COMMERCIAL_SCHEMA))
    op.create_foreign_key(
        "fk_qual_lead_answers_session_id",
        "lead_answers",
        "conversation_sessions",
        ["conversation_session_id"],
        ["id"],
        source_schema=QUALIFICATION_SCHEMA,
        referent_schema=CONVERSATIONS_SCHEMA,
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_qual_lead_answers_session_id",
        "lead_answers",
        schema=QUALIFICATION_SCHEMA,
        type_="foreignkey",
    )
    drop_tables_for_schemas((CONVERSATIONS_SCHEMA, COMMERCIAL_SCHEMA))
