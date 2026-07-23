"""Housing domain ORM models."""

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
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin
from app.db.schemas import CORE_SCHEMA, HOUSING_SCHEMA

_PROJECT_FK = f"{HOUSING_SCHEMA}.projects.id"
_STAGE_FK = f"{HOUSING_SCHEMA}.project_stages.id"
_ALGO_FK = f"{CORE_SCHEMA}.algorithm_versions.id"


class Project(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_housing_projects_canonical_slug", "canonical_slug", unique=True),
        Index("ix_housing_projects_name", "name"),
        Index(
            "ix_housing_projects_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        {"schema": HOUSING_SCHEMA},
    )

    canonical_slug: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    project_type: Mapped[str | None] = mapped_column(String(80))
    available: Mapped[bool] = mapped_column(
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


class ProjectAlias(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "project_aliases"
    __table_args__ = (
        UniqueConstraint("normalized_alias", name="normalized_alias"),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="confidence",
        ),
        Index(
            "ix_housing_project_aliases_normalized_trgm",
            "normalized_alias",
            postgresql_using="gin",
            postgresql_ops={"normalized_alias": "gin_trgm_ops"},
        ),
        {"schema": HOUSING_SCHEMA},
    )

    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_PROJECT_FK, ondelete="CASCADE"),
        nullable=False,
    )
    alias: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str | None] = mapped_column(String(80))
    matching_method: Mapped[str] = mapped_column(String(40), nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))


class ProjectStage(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "project_stages"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="project_id_name"),
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        {"schema": HOUSING_SCHEMA},
    )

    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_PROJECT_FK, ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str | None] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(40))
    available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )


class ProjectLocation(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "project_locations"
    __table_args__ = (
        CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
            name="latitude",
        ),
        CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name="longitude",
        ),
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        {"schema": HOUSING_SCHEMA},
    )

    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_PROJECT_FK, ondelete="CASCADE"),
        nullable=False,
    )
    stage_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_STAGE_FK, ondelete="SET NULL"),
    )
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(160))
    municipality: Mapped[str | None] = mapped_column(String(160))
    department: Mapped[str | None] = mapped_column(String(160))
    country_code: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        server_default=text("'CO'"),
    )
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    source: Mapped[str | None] = mapped_column(String(80))
    reliable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )


class ProjectPrice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "project_prices"
    __table_args__ = (
        CheckConstraint(
            "minimum_price IS NULL OR minimum_price >= 0",
            name="minimum_price",
        ),
        CheckConstraint(
            "maximum_price IS NULL OR maximum_price >= 0",
            name="maximum_price",
        ),
        CheckConstraint(
            "maximum_price IS NULL OR minimum_price IS NULL "
            "OR maximum_price >= minimum_price",
            name="price_range",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="valid_range",
        ),
        {"schema": HOUSING_SCHEMA},
    )

    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_PROJECT_FK, ondelete="CASCADE"),
        nullable=False,
    )
    stage_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_STAGE_FK, ondelete="SET NULL"),
    )
    minimum_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    maximum_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        server_default=text("'COP'"),
    )
    source: Mapped[str | None] = mapped_column(String(80))
    reliable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)


class ProjectAsset(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "project_assets"
    __table_args__ = (
        CheckConstraint(
            "asset_type IN ("
            "'brochure', 'tour_360', 'image', 'video', 'landing_page', 'other')"
            ,
            name="asset_type",
        ),
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        {"schema": HOUSING_SCHEMA},
    )

    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_PROJECT_FK, ondelete="CASCADE"),
        nullable=False,
    )
    asset_type: Mapped[str] = mapped_column(String(40), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str | None] = mapped_column(String(255))
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    is_active: Mapped[bool] = mapped_column(
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


class ProjectAvailability(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "project_availability"
    __table_args__ = (
        CheckConstraint(
            "available_units IS NULL OR available_units >= 0",
            name="available_units",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="valid_range",
        ),
        {"schema": HOUSING_SCHEMA},
    )

    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_PROJECT_FK, ondelete="CASCADE"),
        nullable=False,
    )
    stage_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_STAGE_FK, ondelete="SET NULL"),
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    available_units: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str | None] = mapped_column(String(80))
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProjectHistoricalProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "project_historical_profiles"
    __table_args__ = (
        CheckConstraint("sample_size >= 0", name="sample_size"),
        CheckConstraint(
            "affiliated_percentage IS NULL OR "
            "(affiliated_percentage >= 0 AND affiliated_percentage <= 100)",
            name="affiliated_percentage",
        ),
        CheckConstraint(
            "non_affiliated_percentage IS NULL OR "
            "(non_affiliated_percentage >= 0 AND non_affiliated_percentage <= 100)",
            name="non_affiliated_percentage",
        ),
        CheckConstraint(
            "desistment_percentage IS NULL OR "
            "(desistment_percentage >= 0 AND desistment_percentage <= 100)",
            name="desistment_percentage",
        ),
        Index(
            "ix_housing_project_historical_profiles_project_generated",
            "project_id",
            text("generated_at DESC"),
        ),
        {"schema": HOUSING_SCHEMA},
    )

    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_PROJECT_FK, ondelete="CASCADE"),
        nullable=False,
    )
    sample_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    affiliated_percentage: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    non_affiliated_percentage: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    desistment_percentage: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    profile_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    source_batch_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "ingestion.import_batches.id",
            ondelete="SET NULL",
            name="fk_housing_hist_profiles_batch_id",
            use_alter=True,
        ),
    )
    algorithm_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_ALGO_FK, ondelete="SET NULL"),
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class ProjectProfileDistribution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "project_profile_distributions"
    __table_args__ = (
        UniqueConstraint(
            "historical_profile_id",
            "dimension",
            "value",
            name="profile_dimension_value",
        ),
        CheckConstraint("record_count >= 0", name="record_count"),
        CheckConstraint(
            "percentage IS NULL OR (percentage >= 0 AND percentage <= 100)",
            name="percentage",
        ),
        {"schema": HOUSING_SCHEMA},
    )

    historical_profile_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(f"{HOUSING_SCHEMA}.project_historical_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    dimension: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    percentage: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
