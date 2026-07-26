"""Schemas for phone call product API."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class PhoneLookupRequest(BaseModel):
    document_type: Literal["CC", "CE", "PP", "NIT"] = "CC"
    document_number: str = Field(min_length=3, max_length=32)

    @field_validator("document_number")
    @classmethod
    def strip_document_number(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if len(cleaned) < 3:
            raise ValueError("El número de documento es obligatorio")
        return cleaned


class PhoneLookupResponse(BaseModel):
    known_lead: bool
    has_phone: bool
    nombre: str | None = None
    phone_last4: str | None = None
    message: str


class PhoneCallRequest(BaseModel):
    document_type: Literal["CC", "CE", "PP", "NIT"] = "CC"
    document_number: str = Field(min_length=3, max_length=32)
    data_consent: bool = False
    mode: Literal["now", "schedule"] = "now"
    scheduled_at: datetime | None = None
    # Known lead: confirm the stored phone (last-4 shown in lookup).
    confirm_stored_phone: bool = False
    # New lead / phone update path.
    phone: str | None = Field(default=None, max_length=32)
    country_code: str = Field(default="57", min_length=1, max_length=5)
    nombre: str | None = Field(default=None, max_length=120)

    @field_validator("document_number")
    @classmethod
    def strip_document_number(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if len(cleaned) < 3:
            raise ValueError("El número de documento es obligatorio")
        return cleaned

    @field_validator("nombre")
    @classmethod
    def strip_nombre(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None

    @field_validator("country_code")
    @classmethod
    def strip_country_code(cls, value: str) -> str:
        digits = "".join(ch for ch in (value or "") if ch.isdigit())
        if not digits:
            raise ValueError("El indicativo de país es obligatorio")
        return digits

    @field_validator("phone")
    @classmethod
    def strip_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_call_fields(self) -> "PhoneCallRequest":
        if self.mode == "schedule" and self.scheduled_at is None:
            raise ValueError("scheduled_at is required when mode is schedule")
        if self.confirm_stored_phone:
            return self
        if not self.phone or len(self.phone) < 7:
            raise ValueError("El teléfono es obligatorio")
        if not self.nombre or len(self.nombre) < 2:
            raise ValueError("El nombre es obligatorio")
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
