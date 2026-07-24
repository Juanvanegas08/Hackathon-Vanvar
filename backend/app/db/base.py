"""SQLAlchemy declarative base and reusable mixins."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Integer, MetaData, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.db.naming import NAMING_CONVENTION


class Base(DeclarativeBase):
    """Single declarative base for all CasaLista ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKeyMixin:
    """Native UUID primary key with pgcrypto default."""

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )


class TimestampMixin:
    """created_at timestamp managed in UTC by PostgreSQL."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class UpdatedAtMixin:
    """updated_at timestamp managed in UTC by PostgreSQL."""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class VersionMixin:
    """Optimistic concurrency / profile version counter."""

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("1"),
    )
