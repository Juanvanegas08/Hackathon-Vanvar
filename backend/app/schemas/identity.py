"""Identity lookup and confirmation schemas."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.evaluation import NextQuestion
from app.schemas.lead import LeadResponse


class IdentityLookupRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"document_type": "CC", "document_number": "1000000001"}]
        }
    )

    document_type: str = Field(min_length=1, examples=["CC"])
    document_number: str = Field(min_length=1, examples=["1000000001"])


class IdentityLookupResponse(BaseModel):
    match_status: str
    known_lead: bool
    identity_verified: bool = False
    profile_source: str
    prefilled_profile: dict[str, Any] = Field(default_factory=dict)
    prefilled_fields: list[str] = Field(default_factory=list)
    fields_to_confirm: list[str] = Field(default_factory=list)
    consent_required: bool = True
    demo_mode: bool = True


class LeadFromIdentityRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "document_type": "CC",
                    "document_number": "1000000001",
                    "data_consent": True,
                }
            ]
        }
    )

    document_type: str
    document_number: str
    data_consent: bool = False


class LeadFromIdentityResponse(BaseModel):
    lead: LeadResponse
    identity_context: dict[str, Any]
    next_question: NextQuestion | None = None
    demo_mode: bool = True
    created: bool = True


class FieldConfirmationItem(BaseModel):
    confirmed: bool
    new_value: Any | None = None


class ConfirmPrefilledRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "confirmations": {
                        "salario_mensual": {"confirmed": True},
                        "personas_a_cargo": {"confirmed": False, "new_value": 2},
                    }
                }
            ]
        }
    )

    confirmations: dict[str, FieldConfirmationItem]


class DemoIdentityItem(BaseModel):
    name: str
    document_number: str
    document_type: str
    scenario: str
