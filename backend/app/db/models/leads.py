"""Leads domain ORM models."""

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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin
from app.db.schemas import CORE_SCHEMA, IDENTITY_SCHEMA, LEADS_SCHEMA

_PERSON_FK = f"{IDENTITY_SCHEMA}.persons.id"
_CHANNEL_FK = f"{CORE_SCHEMA}.channels.id"
_SOURCE_FK = f"{CORE_SCHEMA}.data_sources.id"
_LEAD_FK = f"{LEADS_SCHEMA}.leads.id"

_LEAD_STATUS_CHECK = (
    "status IN ("
    "'new', 'profile_incomplete', 'ready_for_advisor', 'nutrition_route', "
    "'non_affiliate_under_review', 'requires_review', 'closed')"
)


class Lead(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "leads"
    __table_args__ = (
        CheckConstraint(_LEAD_STATUS_CHECK, name="status"),
        CheckConstraint(
            "identity_status IN ("
            "'not_checked', 'known_affiliate', 'known_non_affiliate', "
            "'new_lead', 'possible_match', 'identity_not_verified', 'verified'"
            ")",
            name="identity_status",
        ),
        CheckConstraint("current_profile_version >= 1", name="profile_version"),
        CheckConstraint(
            "closed_at IS NULL OR closed_at >= created_at",
            name="closed_after_created",
        ),
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        Index("ix_leads_leads_status_created", "status", text("created_at DESC")),
        Index("ix_leads_leads_person_id", "person_id"),
        Index("ix_leads_leads_channel_id", "channel_id"),
        Index("ix_leads_leads_external_reference", "external_reference"),
        {"schema": LEADS_SCHEMA},
    )

    person_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_PERSON_FK, ondelete="RESTRICT"),
        nullable=False,
    )
    channel_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_CHANNEL_FK, ondelete="SET NULL"),
    )
    external_reference: Mapped[str | None] = mapped_column(String(255))
    campaign_name: Mapped[str | None] = mapped_column(String(255))
    known_lead: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    identity_status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        server_default=text("'not_checked'"),
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'new'"),
    )
    current_profile_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("1"),
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LeadProfile(TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "lead_profiles"
    __table_args__ = (
        CheckConstraint(
            "affiliation_category IS NULL OR affiliation_category IN ('A','B','C','D')",
            name="affiliation_category",
        ),
        CheckConstraint(
            "commercial_segment IS NULL OR commercial_segment IN "
            "('basic', 'medium', 'high', 'young')",
            name="commercial_segment",
        ),
        CheckConstraint(
            "personal_income IS NULL OR personal_income >= 0",
            name="personal_income",
        ),
        CheckConstraint(
            "household_income IS NULL OR household_income >= 0",
            name="household_income",
        ),
        CheckConstraint("savings IS NULL OR savings >= 0", name="savings"),
        CheckConstraint(
            "monthly_obligations IS NULL OR monthly_obligations >= 0",
            name="monthly_obligations",
        ),
        CheckConstraint(
            "household_size IS NULL OR household_size >= 0",
            name="household_size",
        ),
        CheckConstraint(
            "dependents IS NULL OR dependents >= 0",
            name="dependents",
        ),
        CheckConstraint(
            "profile_completeness BETWEEN 0 AND 100",
            name="profile_completeness",
        ),
        CheckConstraint("version >= 1", name="version"),
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        Index(
            "ix_leads_lead_profiles_affiliated_horizon",
            "affiliated",
            "purchase_horizon",
        ),
        {"schema": LEADS_SCHEMA},
    )

    lead_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_LEAD_FK, ondelete="CASCADE"),
        primary_key=True,
    )
    affiliated: Mapped[bool | None] = mapped_column(Boolean)
    affiliation_category: Mapped[str | None] = mapped_column(String(5))
    commercial_segment: Mapped[str | None] = mapped_column(String(40))
    company_name: Mapped[str | None] = mapped_column(String(255))
    personal_income: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    household_income: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    savings: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    monthly_obligations: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    has_home: Mapped[bool | None] = mapped_column(Boolean)
    household_size: Mapped[int | None] = mapped_column(SmallInteger)
    dependents: Mapped[int | None] = mapped_column(SmallInteger)
    beneficiaries_registered: Mapped[bool | None] = mapped_column(Boolean)
    credit_situation: Mapped[str | None] = mapped_column(String(50))
    current_location: Mapped[str | None] = mapped_column(String(255))
    desired_location: Mapped[str | None] = mapped_column(String(255))
    purchase_horizon: Mapped[str | None] = mapped_column(String(50))
    project_interest: Mapped[str | None] = mapped_column(String(255))
    profile_completeness: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        server_default=text("0"),
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("1"),
    )
    additional_preferences: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    profile_document: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )


class LeadFieldMetadata(UpdatedAtMixin, Base):
    __tablename__ = "lead_field_metadata"
    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="confidence",
        ),
        Index(
            "ix_leads_lead_field_metadata_confirmation",
            "lead_id",
            "requires_confirmation",
        ),
        {"schema": LEADS_SCHEMA},
    )

    lead_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_LEAD_FK, ondelete="CASCADE"),
        primary_key=True,
    )
    field_name: Mapped[str] = mapped_column(String(100), primary_key=True)
    source_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_SOURCE_FK, ondelete="SET NULL"),
    )
    confirmed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    requires_confirmation: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )


class LeadProfileChange(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "lead_profile_changes"
    __table_args__ = (
        CheckConstraint("profile_version >= 1", name="profile_version"),
        Index(
            "ix_leads_lead_profile_changes_lead_changed",
            "lead_id",
            text("changed_at DESC"),
        ),
        {"schema": LEADS_SCHEMA},
    )

    lead_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_LEAD_FK, ondelete="CASCADE"),
        nullable=False,
    )
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    new_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    changed_by_type: Mapped[str] = mapped_column(String(40), nullable=False)
    changed_by_id: Mapped[str | None] = mapped_column(String(255))
    source_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_SOURCE_FK, ondelete="SET NULL"),
    )
    reason: Mapped[str | None] = mapped_column(String(255))
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class LeadStatusHistory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "lead_status_history"
    __table_args__ = ({"schema": LEADS_SCHEMA},)

    lead_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_LEAD_FK, ondelete="CASCADE"),
        nullable=False,
    )
    previous_status: Mapped[str | None] = mapped_column(String(50))
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255))
    changed_by_type: Mapped[str | None] = mapped_column(String(40))
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class LeadSourceDetails(TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "lead_source_details"
    __table_args__ = (
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        {"schema": LEADS_SCHEMA},
    )

    lead_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_LEAD_FK, ondelete="CASCADE"),
        primary_key=True,
    )
    source_external_id: Mapped[str | None] = mapped_column(String(255))
    utm_source: Mapped[str | None] = mapped_column(String(255))
    utm_medium: Mapped[str | None] = mapped_column(String(255))
    utm_campaign: Mapped[str | None] = mapped_column(String(255))
    utm_content: Mapped[str | None] = mapped_column(String(255))
    utm_term: Mapped[str | None] = mapped_column(String(255))
    ad_id: Mapped[str | None] = mapped_column(String(255))
    form_id: Mapped[str | None] = mapped_column(String(255))
    landing_page: Mapped[str | None] = mapped_column(String(1000))
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )


class LeadEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "lead_events"
    __table_args__ = (
        Index(
            "ix_leads_lead_events_lead_occurred",
            "lead_id",
            text("occurred_at DESC"),
        ),
        {"schema": LEADS_SCHEMA},
    )

    lead_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_LEAD_FK, ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_type: Mapped[str | None] = mapped_column(String(40))
    actor_id: Mapped[str | None] = mapped_column(String(255))
    request_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
