"""Schemas for phone call product API."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class PhoneCallRequest(BaseModel):
    phone: str = Field(min_length=7, max_length=32)
    mode: Literal["now", "schedule"] = "now"
    scheduled_at: datetime | None = None
    document_type: Literal["CC", "CE", "PP", "NIT"] = "CC"
    document_number: str = Field(min_length=3, max_length=32)
    data_consent: bool = False

    @model_validator(mode="after")
    def validate_schedule(self) -> "PhoneCallRequest":
        if self.mode == "schedule" and self.scheduled_at is None:
            raise ValueError("scheduled_at is required when mode is schedule")
        return self


class PhoneCallResponse(BaseModel):
    mode: Literal["now", "schedule"]
    lead_id: UUID
    phone: str
    call_sid: str | None = None
    scheduled_call_id: UUID | None = None
    scheduled_at: datetime | None = None
    status: str
    message: str
    identity_context: dict[str, Any] = Field(default_factory=dict)
