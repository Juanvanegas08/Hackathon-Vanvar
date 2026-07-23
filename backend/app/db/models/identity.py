"""Identity domain ORM models."""

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
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin
from app.db.schemas import IDENTITY_SCHEMA

_PERSON_FK = f"{IDENTITY_SCHEMA}.persons.id"


class Person(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "persons"
    __table_args__ = (
        CheckConstraint(
            "identity_status IN ("
            "'not_checked', 'known_affiliate', 'known_non_affiliate', "
            "'new_lead', 'possible_match', 'identity_not_verified', 'verified'"
            ")",
            name="identity_status",
        ),
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        {"schema": IDENTITY_SCHEMA},
    )

    first_name: Mapped[str | None] = mapped_column(String(120))
    last_name: Mapped[str | None] = mapped_column(String(120))
    display_name: Mapped[str | None] = mapped_column(String(240))
    identity_status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        server_default=text("'not_checked'"),
    )
    is_demo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )


class PersonIdentifier(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "person_identifiers"
    __table_args__ = (
        UniqueConstraint(
            "identifier_type",
            "country_code",
            "identifier_hash",
            name="identifier_type_country_hash",
        ),
        Index("ix_identity_person_identifiers_person_id", "person_id"),
        Index("ix_identity_person_identifiers_identifier_hash", "identifier_hash"),
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        {"schema": IDENTITY_SCHEMA},
    )

    person_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_PERSON_FK, ondelete="CASCADE"),
        nullable=False,
    )
    identifier_type: Mapped[str] = mapped_column(String(30), nullable=False)
    identifier_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    identifier_ciphertext: Mapped[str | None] = mapped_column(Text)
    identifier_last_four: Mapped[str | None] = mapped_column(String(4))
    country_code: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        server_default=text("'CO'"),
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ContactPoint(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "contact_points"
    __table_args__ = (
        CheckConstraint("contact_type IN ('phone', 'email')", name="contact_type"),
        UniqueConstraint("contact_type", "value_hash", name="contact_type_value_hash"),
        Index("ix_identity_contact_points_value_hash", "value_hash"),
        CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        {"schema": IDENTITY_SCHEMA},
    )

    person_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_PERSON_FK, ondelete="CASCADE"),
        nullable=False,
    )
    contact_type: Mapped[str] = mapped_column(String(30), nullable=False)
    value_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    value_ciphertext: Mapped[str | None] = mapped_column(Text)
    masked_value: Mapped[str | None] = mapped_column(String(255))
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Consent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "consents"
    __table_args__ = (
        CheckConstraint(
            "revoked_at IS NULL OR granted_at IS NULL OR revoked_at >= granted_at",
            name="revoked_after_granted",
        ),
        CheckConstraint(
            "expires_at IS NULL OR granted_at IS NULL OR expires_at >= granted_at",
            name="expires_after_granted",
        ),
        {"schema": IDENTITY_SCHEMA},
    )

    person_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_PERSON_FK, ondelete="CASCADE"),
        nullable=False,
    )
    consent_type: Mapped[str] = mapped_column(String(80), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    version: Mapped[str | None] = mapped_column(String(40))
    channel: Mapped[str | None] = mapped_column(String(40))
    ip_hash: Mapped[str | None] = mapped_column(String(128))
    user_agent_hash: Mapped[str | None] = mapped_column(String(128))
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )


class IdentityLookupEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "identity_lookup_events"
    __table_args__ = (
        CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="latency_ms"),
        CheckConstraint(
            "responded_at IS NULL OR responded_at >= requested_at",
            name="responded_after_requested",
        ),
        Index(
            "ix_identity_identity_lookup_events_hash_requested",
            "identifier_hash",
            text("requested_at DESC"),
        ),
        {"schema": IDENTITY_SCHEMA},
    )

    identifier_type: Mapped[str] = mapped_column(String(30), nullable=False)
    identifier_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    match_status: Mapped[str] = mapped_column(String(40), nullable=False)
    matched_person_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_PERSON_FK, ondelete="SET NULL"),
    )
    request_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    demo_mode: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(80))
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )


class IdentityMatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "identity_matches"
    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="confidence",
        ),
        {"schema": IDENTITY_SCHEMA},
    )

    lookup_event_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(f"{IDENTITY_SCHEMA}.identity_lookup_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    person_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(_PERSON_FK, ondelete="SET NULL"),
    )
    match_status: Mapped[str] = mapped_column(String(40), nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    reason: Mapped[str | None] = mapped_column(Text)
    is_selected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
