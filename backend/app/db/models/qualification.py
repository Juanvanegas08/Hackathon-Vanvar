"""Qualification domain ORM models."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin
from app.db.schemas import CORE_SCHEMA, LEADS_SCHEMA, QUALIFICATION_SCHEMA

_LEAD_FK = f"{LEADS_SCHEMA}.leads.id"
_SOURCE_FK = f"{CORE_SCHEMA}.data_sources.id"
_ALGO_FK = f"{CORE_SCHEMA}.algorithm_versions.id"
_QUESTION_FK = f"{QUALIFICATION_SCHEMA}.question_definitions.id"
_ASSESSMENT_FK = f"{QUALIFICATION_SCHEMA}.assessments.id"
_PLAN_FK = f"{QUALIFICATION_SCHEMA}.nutrition_plans.id"


class QuestionDefinition(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "question_definitions"
    __table_args__ = (
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        {"schema": QUALIFICATION_SCHEMA},
    )

    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    profile_field: Mapped[str] = mapped_column(String(100), nullable=False)
    question_type: Mapped[str] = mapped_column(String(40), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    confirmation_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    validation_rules: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )


class LeadAnswer(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "lead_answers"
    __table_args__ = (
        CheckConstraint("profile_version >= 1", name="profile_version"),
        Index(
            "ix_qualification_lead_answers_lead_answered",
            "lead_id",
            text("answered_at DESC"),
        ),
        {"schema": QUALIFICATION_SCHEMA},
    )

    lead_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_LEAD_FK, ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_QUESTION_FK, ondelete="SET NULL"),
    )
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False)
    normalized_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    raw_text_redacted: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_SOURCE_FK, ondelete="SET NULL"),
    )
    confirmed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    conversation_session_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "conversations.conversation_sessions.id",
            ondelete="SET NULL",
            name="fk_qual_lead_answers_session_id",
            use_alter=True,
        ),
    )


class Assessment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assessments"
    __table_args__ = (
        CheckConstraint(
            "readiness_score BETWEEN 0 AND 100",
            name="readiness_score",
        ),
        CheckConstraint("profile_version >= 1", name="profile_version"),
        CheckConstraint(
            "confidence IN ('low', 'medium', 'high')",
            name="confidence",
        ),
        Index(
            "ix_qualification_assessments_lead_created",
            "lead_id",
            text("created_at DESC"),
        ),
        {"schema": QUALIFICATION_SCHEMA},
    )

    lead_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_LEAD_FK, ondelete="RESTRICT"),
        nullable=False,
    )
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False)
    readiness_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    primary_gap: Mapped[str | None] = mapped_column(String(100))
    next_action: Mapped[str | None] = mapped_column(String(100))
    algorithm_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_ALGO_FK, ondelete="RESTRICT"),
    )
    disclaimer: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )


class AssessmentFactor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_factors"
    __table_args__ = (
        CheckConstraint("contribution >= 0", name="contribution"),
        CheckConstraint("maximum_weight >= 0", name="maximum_weight"),
        CheckConstraint(
            "contribution <= maximum_weight",
            name="contribution_vs_weight",
        ),
        {"schema": QUALIFICATION_SCHEMA},
    )

    assessment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_ASSESSMENT_FK, ondelete="CASCADE"),
        nullable=False,
    )
    factor_code: Mapped[str] = mapped_column(String(100), nullable=False)
    result: Mapped[str | None] = mapped_column(String(40))
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


class NutritionPlan(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "nutrition_plans"
    __table_args__ = (
        CheckConstraint(
            "monthly_saving_goal IS NULL OR monthly_saving_goal >= 0",
            name="monthly_saving_goal",
        ),
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        {"schema": QUALIFICATION_SCHEMA},
    )

    lead_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_LEAD_FK, ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    primary_gap: Mapped[str] = mapped_column(String(100), nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date)
    monthly_saving_goal: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    plan_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )


class NutritionAction(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "nutrition_actions"
    __table_args__ = (
        CheckConstraint(
            "completed_at IS NULL OR scheduled_at IS NULL "
            "OR completed_at >= scheduled_at",
            name="completed_after_scheduled",
        ),
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        {"schema": QUALIFICATION_SCHEMA},
    )

    nutrition_plan_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_PLAN_FK, ondelete="CASCADE"),
        nullable=False,
    )
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
