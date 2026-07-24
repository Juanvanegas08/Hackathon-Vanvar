"""Audit domain ORM models."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin
from app.db.schemas import AUDIT_SCHEMA


class AuditEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index(
            "ix_audit_audit_events_entity",
            "entity_schema",
            "entity_table",
            "entity_id",
        ),
        {"schema": AUDIT_SCHEMA},
    )

    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_schema: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_table: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    changed_fields: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    request_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )


class IntegrationEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "integration_events"
    __table_args__ = (
        CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="latency_ms"),
        Index(
            "ix_audit_integration_events_provider_created",
            "provider",
            text("created_at DESC"),
        ),
        {"schema": AUDIT_SCHEMA},
    )

    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    operation: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    request_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    external_reference: Mapped[str | None] = mapped_column(String(255))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(100))
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )


class SecurityEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "security_events"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('info', 'warning', 'error', 'critical')",
            name="severity",
        ),
        {"schema": AUDIT_SCHEMA},
    )

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_reference_hash: Mapped[str | None] = mapped_column(String(128))
    ip_hash: Mapped[str | None] = mapped_column(String(128))
    request_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )


class OutboxEvent(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        CheckConstraint("attempts >= 0", name="attempts"),
        CheckConstraint(
            "processed_at IS NULL OR processed_at >= created_at",
            name="processed_after_created",
        ),
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        Index(
            "ix_audit_outbox_events_pending_available",
            "available_at",
            postgresql_where=text("status = 'pending'"),
        ),
        {"schema": AUDIT_SCHEMA},
    )

    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'pending'"),
    )
    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
