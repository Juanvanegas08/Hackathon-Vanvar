"""Recommendations domain ORM models."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.schemas import (
    CORE_SCHEMA,
    HOUSING_SCHEMA,
    LEADS_SCHEMA,
    QUALIFICATION_SCHEMA,
    RECOMMENDATIONS_SCHEMA,
)

_LEAD_FK = f"{LEADS_SCHEMA}.leads.id"
_PROJECT_FK = f"{HOUSING_SCHEMA}.projects.id"
_ALGO_FK = f"{CORE_SCHEMA}.algorithm_versions.id"
_ASSESSMENT_FK = f"{QUALIFICATION_SCHEMA}.assessments.id"
_RUN_FK = f"{RECOMMENDATIONS_SCHEMA}.recommendation_runs.id"
_ITEM_FK = f"{RECOMMENDATIONS_SCHEMA}.recommendation_items.id"


class RecommendationRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "recommendation_runs"
    __table_args__ = (
        CheckConstraint("profile_version >= 1", name="profile_version"),
        CheckConstraint(
            "evaluated_project_count >= 0",
            name="evaluated_project_count",
        ),
        CheckConstraint(
            "overall_confidence IN ('low', 'medium', 'high')",
            name="overall_confidence",
        ),
        Index(
            "ix_recommendations_recommendation_runs_lead_generated",
            "lead_id",
            text("generated_at DESC"),
        ),
        {"schema": RECOMMENDATIONS_SCHEMA},
    )

    lead_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_LEAD_FK, ondelete="RESTRICT"),
        nullable=False,
    )
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False)
    assessment_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_ASSESSMENT_FK, ondelete="SET NULL"),
    )
    algorithm_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_ALGO_FK, ondelete="RESTRICT"),
    )
    evaluated_project_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    overall_confidence: Mapped[str] = mapped_column(String(20), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )


class RecommendationItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recommendation_items"
    __table_args__ = (
        UniqueConstraint(
            "recommendation_run_id",
            "project_id",
            name="run_project",
        ),
        UniqueConstraint(
            "recommendation_run_id",
            "rank",
            name="run_rank",
        ),
        CheckConstraint("rank >= 1", name="rank"),
        CheckConstraint(
            "compatibility_score >= 0 AND compatibility_score <= 100",
            name="compatibility_score",
        ),
        CheckConstraint(
            "confidence IN ('low', 'medium', 'high')",
            name="confidence",
        ),
        Index(
            "ix_recommendations_recommendation_items_run_rank",
            "recommendation_run_id",
            "rank",
        ),
        {"schema": RECOMMENDATIONS_SCHEMA},
    )

    recommendation_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_RUN_FK, ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_PROJECT_FK, ondelete="RESTRICT"),
        nullable=False,
    )
    rank: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    compatibility_score: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False)
    warnings: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )


class RecommendationFactor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recommendation_factors"
    __table_args__ = (
        CheckConstraint("contribution >= 0", name="contribution"),
        CheckConstraint("maximum_weight >= 0", name="maximum_weight"),
        CheckConstraint(
            "contribution <= maximum_weight",
            name="contribution_vs_weight",
        ),
        {"schema": RECOMMENDATIONS_SCHEMA},
    )

    recommendation_item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_ITEM_FK, ondelete="CASCADE"),
        nullable=False,
    )
    criterion: Mapped[str] = mapped_column(String(100), nullable=False)
    matched: Mapped[bool | None] = mapped_column(Boolean)
    contribution: Mapped[Decimal] = mapped_column(
        Numeric(7, 4),
        nullable=False,
        server_default=text("0"),
    )
    maximum_weight: Mapped[Decimal] = mapped_column(
        Numeric(7, 4),
        nullable=False,
        server_default=text("0"),
    )
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )


class RecommendationFeedback(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "recommendation_feedback"
    __table_args__ = (
        CheckConstraint(
            "action IN ("
            "'interested', 'not_interested', 'viewed_brochure', "
            "'viewed_tour', 'requested_appointment')"
            ,
            name="action",
        ),
        {"schema": RECOMMENDATIONS_SCHEMA},
    )

    lead_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_LEAD_FK, ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_PROJECT_FK, ondelete="RESTRICT"),
        nullable=False,
    )
    recommendation_item_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_ITEM_FK, ondelete="SET NULL"),
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
