"""Affiliation domain ORM models."""

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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin
from app.db.schemas import AFFILIATION_SCHEMA, IDENTITY_SCHEMA

_PERSON_FK = f"{IDENTITY_SCHEMA}.persons.id"
_RECORD_FK = f"{AFFILIATION_SCHEMA}.affiliation_records.id"


class AffiliationRecord(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "affiliation_records"
    __table_args__ = (
        CheckConstraint(
            "status IN ("
            "'unknown', 'affiliated', 'non_affiliated', 'former_affiliate', 'pending'"
            ")",
            name="status",
        ),
        CheckConstraint(
            "category IS NULL OR category IN ('A', 'B', 'C', 'D')",
            name="category",
        ),
        CheckConstraint(
            "reported_salary IS NULL OR reported_salary >= 0",
            name="reported_salary",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL "
            "OR effective_to >= effective_from",
            name="effective_range",
        ),
        Index(
            "ix_affiliation_affiliation_records_person_effective",
            "person_id",
            "effective_to",
        ),
        Index(
            "ix_affiliation_affiliation_records_status_category",
            "status",
            "category",
        ),
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        {"schema": AFFILIATION_SCHEMA},
    )

    person_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_PERSON_FK, ondelete="RESTRICT"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    category: Mapped[str | None] = mapped_column(String(5))
    reported_salary: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    confirmed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    source_reference: Mapped[str | None] = mapped_column(String(255))
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)


class AffiliationCategoryHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "affiliation_category_history"
    __table_args__ = (
        CheckConstraint(
            "previous_category IS NULL OR previous_category IN ('A', 'B', 'C', 'D')",
            name="previous_category",
        ),
        CheckConstraint(
            "new_category IS NULL OR new_category IN ('A', 'B', 'C', 'D')",
            name="new_category",
        ),
        CheckConstraint(
            "reported_salary IS NULL OR reported_salary >= 0",
            name="reported_salary",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="effective_range",
        ),
        {"schema": AFFILIATION_SCHEMA},
    )

    affiliation_record_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_RECORD_FK, ondelete="CASCADE"),
        nullable=False,
    )
    previous_category: Mapped[str | None] = mapped_column(String(5))
    new_category: Mapped[str | None] = mapped_column(String(5))
    reported_salary: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    reason: Mapped[str | None] = mapped_column(String(255))
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)


class AffiliationEmployer(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "affiliation_employers"
    __table_args__ = (
        CheckConstraint(
            "reported_salary IS NULL OR reported_salary >= 0",
            name="reported_salary",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL "
            "OR effective_to >= effective_from",
            name="effective_range",
        ),
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        {"schema": AFFILIATION_SCHEMA},
    )

    affiliation_record_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_RECORD_FK, ondelete="CASCADE"),
        nullable=False,
    )
    employer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    employer_identifier_hash: Mapped[str | None] = mapped_column(String(128))
    reported_salary: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )


class AffiliationBeneficiary(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "affiliation_beneficiaries"
    __table_args__ = (
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL "
            "OR effective_to >= effective_from",
            name="effective_range",
        ),
        {"schema": AFFILIATION_SCHEMA},
    )

    affiliation_record_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_RECORD_FK, ondelete="CASCADE"),
        nullable=False,
    )
    relationship_type: Mapped[str | None] = mapped_column(String(50))
    beneficiary_reference_hash: Mapped[str | None] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)


class AffiliationLookupLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "affiliation_lookup_logs"
    __table_args__ = (
        CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="latency_ms"),
        CheckConstraint(
            "responded_at IS NULL OR responded_at >= requested_at",
            name="responded_after_requested",
        ),
        {"schema": AFFILIATION_SCHEMA},
    )

    person_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_PERSON_FK, ondelete="SET NULL"),
    )
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    request_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(80))
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
