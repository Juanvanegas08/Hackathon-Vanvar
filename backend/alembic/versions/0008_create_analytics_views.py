"""0008 create analytics views.

Revision ID: 0008_analytics_views
Revises: 0007_ingestion_audit
Create Date: 2026-07-23
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from app.db.schemas import ANALYTICS_SCHEMA
from sqlalchemy import text

revision: str = "0008_analytics_views"
down_revision: str | None = "0007_ingestion_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEAD_FUNNEL_VIEW = f"""
CREATE OR REPLACE VIEW {ANALYTICS_SCHEMA}.lead_funnel AS
SELECT
    l.status,
    lp.affiliated,
    l.channel_id,
    COUNT(*)::bigint AS lead_count,
    (l.created_at AT TIME ZONE 'UTC')::date AS created_date
FROM leads.leads AS l
LEFT JOIN leads.lead_profiles AS lp ON lp.lead_id = l.id
GROUP BY l.status, lp.affiliated, l.channel_id, (l.created_at AT TIME ZONE 'UTC')::date
"""

PROJECT_INTEREST_VIEW = f"""
CREATE OR REPLACE VIEW {ANALYTICS_SCHEMA}.project_interest AS
SELECT
    p.id AS project_id,
    p.name AS project_name,
    COUNT(DISTINCT ri.id)::bigint AS recommended_count,
    COUNT(*) FILTER (WHERE rf.action = 'interested')::bigint AS interested_count,
    COUNT(*) FILTER (WHERE rf.action = 'viewed_brochure')::bigint AS brochure_views,
    COUNT(*) FILTER (WHERE rf.action = 'viewed_tour')::bigint AS tour_views,
    COUNT(*) FILTER (WHERE rf.action = 'requested_appointment')::bigint AS appointment_requests
FROM housing.projects AS p
LEFT JOIN recommendations.recommendation_items AS ri ON ri.project_id = p.id
LEFT JOIN recommendations.recommendation_feedback AS rf ON rf.project_id = p.id
GROUP BY p.id, p.name
"""

CONVERSATION_PERFORMANCE_VIEW = f"""
CREATE OR REPLACE VIEW {ANALYTICS_SCHEMA}.conversation_performance AS
SELECT
    cs.channel,
    cs.provider,
    COUNT(*)::bigint AS sessions_count,
    COUNT(*) FILTER (WHERE cs.ended_at IS NOT NULL)::bigint AS completed_count,
    AVG(cs.duration_seconds)::double precision AS average_duration_seconds,
    AVG(cm.questions_asked)::double precision AS average_questions,
    AVG(cm.completion_percentage)::double precision AS average_completion_percentage
FROM conversations.conversation_sessions AS cs
LEFT JOIN conversations.conversation_metrics AS cm ON cm.session_id = cs.id
GROUP BY cs.channel, cs.provider
"""


def upgrade() -> None:
    op.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{ANALYTICS_SCHEMA}"'))
    op.execute(text(LEAD_FUNNEL_VIEW))
    op.execute(text(PROJECT_INTEREST_VIEW))
    op.execute(text(CONVERSATION_PERFORMANCE_VIEW))
    op.execute(
        text(
            f"""
            COMMENT ON VIEW {ANALYTICS_SCHEMA}.lead_funnel IS
            'casalista_analytics_view;is_view=true'
            """
        )
    )
    op.execute(
        text(
            f"""
            COMMENT ON VIEW {ANALYTICS_SCHEMA}.project_interest IS
            'casalista_analytics_view;is_view=true'
            """
        )
    )
    op.execute(
        text(
            f"""
            COMMENT ON VIEW {ANALYTICS_SCHEMA}.conversation_performance IS
            'casalista_analytics_view;is_view=true'
            """
        )
    )


def downgrade() -> None:
    op.execute(text(f"DROP VIEW IF EXISTS {ANALYTICS_SCHEMA}.conversation_performance"))
    op.execute(text(f"DROP VIEW IF EXISTS {ANALYTICS_SCHEMA}.project_interest"))
    op.execute(text(f"DROP VIEW IF EXISTS {ANALYTICS_SCHEMA}.lead_funnel"))
