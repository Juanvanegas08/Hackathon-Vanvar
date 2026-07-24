"""Conversations domain ORM models."""

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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin
from app.db.schemas import CONVERSATIONS_SCHEMA, LEADS_SCHEMA

_LEAD_FK = f"{LEADS_SCHEMA}.leads.id"
_SESSION_FK = f"{CONVERSATIONS_SCHEMA}.conversation_sessions.id"


class ConversationSession(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "conversation_sessions"
    __table_args__ = (
        CheckConstraint(
            "channel IN ("
            "'voice_web', 'voice_phone', 'text_web', 'whatsapp', 'contact_center')"
            ,
            name="channel",
        ),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="duration_seconds",
        ),
        CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at",
            name="ended_after_started",
        ),
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        Index(
            "ix_conversations_conversation_sessions_lead_started",
            "lead_id",
            text("started_at DESC"),
        ),
        {"schema": CONVERSATIONS_SCHEMA},
    )

    lead_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_LEAD_FK, ondelete="CASCADE"),
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(String(40), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(80))
    provider_session_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    completion_reason: Mapped[str | None] = mapped_column(String(100))
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )


class ConversationEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "conversation_events"
    __table_args__ = ({"schema": CONVERSATIONS_SCHEMA},)

    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_SESSION_FK, ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    profile_field: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str | None] = mapped_column(String(40))
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


class ToolExecution(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "tool_executions"
    __table_args__ = (
        CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="latency_ms"),
        Index(
            "ix_conversations_tool_executions_session_created",
            "session_id",
            "created_at",
        ),
        {"schema": CONVERSATIONS_SCHEMA},
    )

    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_SESSION_FK, ondelete="CASCADE"),
        nullable=False,
    )
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    request_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
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


class ConversationMetrics(TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "conversation_metrics"
    __table_args__ = (
        CheckConstraint("questions_asked >= 0", name="questions_asked"),
        CheckConstraint("fields_confirmed >= 0", name="fields_confirmed"),
        CheckConstraint("clarifications >= 0", name="clarifications"),
        CheckConstraint("interruptions >= 0", name="interruptions"),
        CheckConstraint(
            "completion_percentage BETWEEN 0 AND 100",
            name="completion_percentage",
        ),
        CheckConstraint("input_audio_seconds >= 0", name="input_audio_seconds"),
        CheckConstraint("output_audio_seconds >= 0", name="output_audio_seconds"),
        CheckConstraint(
            "estimated_cost IS NULL OR estimated_cost >= 0",
            name="estimated_cost",
        ),
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        {"schema": CONVERSATIONS_SCHEMA},
    )

    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_SESSION_FK, ondelete="CASCADE"),
        primary_key=True,
    )
    questions_asked: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    fields_confirmed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    clarifications: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    interruptions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    completion_percentage: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        server_default=text("0"),
    )
    input_audio_seconds: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default=text("0"),
    )
    output_audio_seconds: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default=text("0"),
    )
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))


class ConversationMessage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "conversation_messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant', 'system', 'tool')",
            name="role",
        ),
        {"schema": CONVERSATIONS_SCHEMA},
    )

    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_SESSION_FK, ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content_redacted: Mapped[str | None] = mapped_column(Text)
    message_type: Mapped[str] = mapped_column(String(30), nullable=False)
    persisted_with_consent: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
