"""Commercial domain ORM models."""

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
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin
from app.db.schemas import COMMERCIAL_SCHEMA, HOUSING_SCHEMA, LEADS_SCHEMA

_LEAD_FK = f"{LEADS_SCHEMA}.leads.id"
_PROJECT_FK = f"{HOUSING_SCHEMA}.projects.id"
_ADVISOR_FK = f"{COMMERCIAL_SCHEMA}.advisors.id"
_PERIOD_FK = f"{COMMERCIAL_SCHEMA}.regulatory_periods.id"


class Advisor(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "advisors"
    __table_args__ = (
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        {"schema": COMMERCIAL_SCHEMA},
    )

    external_reference: Mapped[str | None] = mapped_column(String(255), unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(CITEXT)
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )


class AdvisorQueue(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "advisor_queue"
    __table_args__ = (
        CheckConstraint(
            "priority_score >= 0 AND priority_score <= 100",
            name="priority_score",
        ),
        CheckConstraint(
            "expires_at IS NULL OR expires_at >= entered_at",
            name="expires_after_entered",
        ),
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        Index(
            "ix_commercial_advisor_queue_status_priority",
            "status",
            text("priority_score DESC"),
        ),
        {"schema": COMMERCIAL_SCHEMA},
    )

    lead_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_LEAD_FK, ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    priority_score: Mapped[Decimal] = mapped_column(
        Numeric(7, 4),
        nullable=False,
        server_default=text("0"),
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255))
    recommended_project_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_PROJECT_FK, ondelete="SET NULL"),
    )
    entered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AdvisorAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "advisor_assignments"
    __table_args__ = (
        CheckConstraint(
            "released_at IS NULL OR released_at >= assigned_at",
            name="released_after_assigned",
        ),
        {"schema": COMMERCIAL_SCHEMA},
    )

    lead_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_LEAD_FK, ondelete="CASCADE"),
        nullable=False,
    )
    advisor_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_ADVISOR_FK, ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(String(255))


class Appointment(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        Index(
            "ix_commercial_appointments_lead_scheduled",
            "lead_id",
            text("scheduled_at DESC"),
        ),
        {"schema": COMMERCIAL_SCHEMA},
    )

    lead_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_LEAD_FK, ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_PROJECT_FK, ondelete="SET NULL"),
    )
    advisor_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_ADVISOR_FK, ondelete="SET NULL"),
    )
    appointment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    notes_redacted: Mapped[str | None] = mapped_column(Text)
    external_reference: Mapped[str | None] = mapped_column(String(255))


class FollowUpTask(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "follow_up_tasks"
    __table_args__ = (
        CheckConstraint(
            "completed_at IS NULL OR due_at IS NULL OR completed_at >= due_at",
            name="completed_after_due",
        ),
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        {"schema": COMMERCIAL_SCHEMA},
    )

    lead_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_LEAD_FK, ondelete="CASCADE"),
        nullable=False,
    )
    advisor_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_ADVISOR_FK, ondelete="SET NULL"),
    )
    task_type: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), nullable=False)


class CommercialOutcome(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "commercial_outcomes"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ("
            "'visit_scheduled', 'visited', 'separation_started', "
            "'sale_completed', 'desisted', 'lost')"
            ,
            name="outcome",
        ),
        {"schema": COMMERCIAL_SCHEMA},
    )

    lead_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_LEAD_FK, ondelete="RESTRICT"),
        nullable=False,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_PROJECT_FK, ondelete="RESTRICT"),
    )
    outcome: Mapped[str] = mapped_column(String(50), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    external_reference: Mapped[str | None] = mapped_column(String(255))
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )


class RegulatoryPeriod(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "regulatory_periods"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="date_range"),
        CheckConstraint(
            "minimum_affiliated_percentage >= 0 "
            "AND minimum_affiliated_percentage <= 100",
            name="minimum_affiliated_percentage",
        ),
        CheckConstraint(
            "maximum_non_affiliated_percentage >= 0 "
            "AND maximum_non_affiliated_percentage <= 100",
            name="maximum_non_affiliated_percentage",
        ),
        CheckConstraint(
            "minimum_affiliated_percentage + maximum_non_affiliated_percentage <= 100",
            name="percentage_sum",
        ),
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        {"schema": COMMERCIAL_SCHEMA},
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    minimum_affiliated_percentage: Mapped[Decimal] = mapped_column(
        Numeric(7, 4),
        nullable=False,
        server_default=text("90"),
    )
    maximum_non_affiliated_percentage: Mapped[Decimal] = mapped_column(
        Numeric(7, 4),
        nullable=False,
        server_default=text("10"),
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)


class RegulatorySnapshot(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "regulatory_snapshots"
    __table_args__ = (
        CheckConstraint("affiliated_sales >= 0", name="affiliated_sales"),
        CheckConstraint("non_affiliated_sales >= 0", name="non_affiliated_sales"),
        CheckConstraint("total_sales >= 0", name="total_sales"),
        CheckConstraint(
            "available_non_affiliated_slots IS NULL "
            "OR available_non_affiliated_slots >= 0",
            name="available_non_affiliated_slots",
        ),
        CheckConstraint(
            "total_sales = affiliated_sales + non_affiliated_sales",
            name="total_sales_sum",
        ),
        Index(
            "ix_commercial_regulatory_snapshots_period_calculated",
            "period_id",
            text("calculated_at DESC"),
        ),
        {"schema": COMMERCIAL_SCHEMA},
    )

    period_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_PERIOD_FK, ondelete="CASCADE"),
        nullable=False,
    )
    affiliated_sales: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    non_affiliated_sales: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    total_sales: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    available_non_affiliated_slots: Mapped[int | None] = mapped_column(Integer)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
