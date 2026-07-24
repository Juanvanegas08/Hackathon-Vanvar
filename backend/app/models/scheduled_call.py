"""In-memory scheduled outbound phone call domain model."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ScheduledCallStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScheduledPhoneCall(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    lead_id: UUID
    phone: str
    scheduled_at: datetime
    status: ScheduledCallStatus = ScheduledCallStatus.PENDING
    call_sid: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now().astimezone())
    updated_at: datetime = Field(default_factory=lambda: datetime.now().astimezone())
