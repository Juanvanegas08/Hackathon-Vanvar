"""Core domain ORM models."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin
from app.db.schemas import CORE_SCHEMA


class AppSetting(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "app_settings"
    __table_args__ = (
        CheckConstraint(
            "value_type IN ('string', 'integer', 'decimal', 'boolean', 'json')",
            name="value_type",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="valid_range",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="updated_after_created",
        ),
        {"schema": CORE_SCHEMA},
    )

    key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    value_type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )


class DataSource(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "data_sources"
    __table_args__ = (
        CheckConstraint("trust_level BETWEEN 0 AND 100", name="trust_level"),
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        {"schema": CORE_SCHEMA},
    )

    code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    trust_level: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        server_default=text("50"),
    )
    is_official: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )


class Channel(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "channels"
    __table_args__ = (
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        {"schema": CORE_SCHEMA},
    )

    code: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_voice: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    is_paid: Mapped[bool | None] = mapped_column(Boolean)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )


class AlgorithmVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "algorithm_versions"
    __table_args__ = (
        UniqueConstraint("algorithm_type", "version", name="algorithm_type_version"),
        {"schema": CORE_SCHEMA},
    )

    algorithm_type: Mapped[str] = mapped_column(String(80), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FeatureFlag(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "feature_flags"
    __table_args__ = (
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        {"schema": CORE_SCHEMA},
    )

    key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    configuration: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    description: Mapped[str | None] = mapped_column(Text)


