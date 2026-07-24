"""Ingestion domain ORM models."""

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
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin
from app.db.schemas import HOUSING_SCHEMA, IDENTITY_SCHEMA, INGESTION_SCHEMA

_BATCH_FK = f"{INGESTION_SCHEMA}.import_batches.id"
_PROJECT_FK = f"{HOUSING_SCHEMA}.projects.id"
_PERSON_FK = f"{IDENTITY_SCHEMA}.persons.id"


class ImportBatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "import_batches"
    __table_args__ = (
        UniqueConstraint("file_checksum", "source_name", name="checksum_source"),
        CheckConstraint("total_records >= 0", name="total_records"),
        CheckConstraint("valid_records >= 0", name="valid_records"),
        CheckConstraint("invalid_records >= 0", name="invalid_records"),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="completed_after_started",
        ),
        Index("ix_ingestion_import_batches_file_checksum", "file_checksum"),
        {"schema": INGESTION_SCHEMA},
    )

    source_name: Mapped[str] = mapped_column(String(160), nullable=False)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    total_records: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    valid_records: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    invalid_records: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )


class RawRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "raw_records"
    __table_args__ = (
        UniqueConstraint(
            "batch_id",
            "row_number",
            "entity_type",
            name="batch_row_entity",
        ),
        CheckConstraint("row_number >= 0", name="row_number"),
        Index(
            "ix_ingestion_raw_records_batch_processed",
            "batch_id",
            "processed",
        ),
        {"schema": INGESTION_SCHEMA},
    )

    batch_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_BATCH_FK, ondelete="CASCADE"),
        nullable=False,
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    processed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )


class NormalizedBuyerRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "normalized_buyer_records"
    __table_args__ = (
        UniqueConstraint("batch_id", "row_number", name="batch_row"),
        CheckConstraint("row_number >= 0", name="row_number"),
        CheckConstraint(
            "dependents IS NULL OR dependents >= 0",
            name="dependents",
        ),
        CheckConstraint(
            "housing_value IS NULL OR housing_value >= 0",
            name="housing_value",
        ),
        CheckConstraint(
            "affiliation_category IS NULL OR affiliation_category IN ('A','B','C','D')",
            name="affiliation_category",
        ),
        Index("ix_ingestion_normalized_buyer_records_person_id", "person_id"),
        {"schema": INGESTION_SCHEMA},
    )

    batch_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_BATCH_FK, ondelete="CASCADE"),
        nullable=False,
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    person_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_PERSON_FK, ondelete="SET NULL"),
    )
    historical_project_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_PROJECT_FK, ondelete="SET NULL"),
    )
    original_project_name: Mapped[str | None] = mapped_column(String(255))
    affiliation_status: Mapped[str | None] = mapped_column(String(50))
    affiliation_category: Mapped[str | None] = mapped_column(String(5))
    commercial_segment: Mapped[str | None] = mapped_column(String(50))
    salary_range: Mapped[str | None] = mapped_column(String(100))
    dependents: Mapped[int | None] = mapped_column(SmallInteger)
    company_name: Mapped[str | None] = mapped_column(String(255))
    financial_entity: Mapped[str | None] = mapped_column(String(255))
    housing_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    housing_value_reliable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    option_date: Mapped[date | None] = mapped_column(Date)
    desistment_date: Mapped[date | None] = mapped_column(Date)
    normalized_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )


class NormalizationIssue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "normalization_issues"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('info', 'warning', 'error', 'critical')",
            name="severity",
        ),
        Index(
            "ix_ingestion_normalization_issues_batch_severity",
            "batch_id",
            "severity",
            "resolved",
        ),
        {"schema": INGESTION_SCHEMA},
    )

    batch_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_BATCH_FK, ondelete="CASCADE"),
        nullable=False,
    )
    row_number: Mapped[int | None] = mapped_column(Integer)
    field_name: Mapped[str | None] = mapped_column(String(120))
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    issue_code: Mapped[str] = mapped_column(String(100), nullable=False)
    original_value: Mapped[str | None] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    resolution_note: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EntityMatchCandidate(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "entity_match_candidates"
    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="confidence",
        ),
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        {"schema": INGESTION_SCHEMA},
    )

    batch_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_BATCH_FK, ondelete="CASCADE"),
        nullable=False,
    )
    source_entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_value: Mapped[str] = mapped_column(String(500), nullable=False)
    target_entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    match_method: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )


class SeedExecution(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "seed_executions"
    __table_args__ = (
        UniqueConstraint(
            "seed_name",
            "seed_version",
            "checksum",
            name="seed_name_version_checksum",
        ),
        CheckConstraint("records_inserted >= 0", name="records_inserted"),
        CheckConstraint("records_updated >= 0", name="records_updated"),
        CheckConstraint("records_skipped >= 0", name="records_skipped"),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="completed_after_started",
        ),
        {"schema": INGESTION_SCHEMA},
    )

    seed_name: Mapped[str] = mapped_column(String(160), nullable=False)
    seed_version: Mapped[str] = mapped_column(String(50), nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    records_inserted: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    records_updated: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    records_skipped: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
