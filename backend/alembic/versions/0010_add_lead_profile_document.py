"""0010 add lead profile document JSONB.

Revision ID: 0010_lead_profile_document
Revises: 0009_buyer_person_link
Create Date: 2026-07-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_lead_profile_document"
down_revision: str | None = "0009_buyer_person_link"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "lead_profiles",
        sa.Column(
            "profile_document",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        schema="leads",
    )


def downgrade() -> None:
    op.drop_column("lead_profiles", "profile_document", schema="leads")
