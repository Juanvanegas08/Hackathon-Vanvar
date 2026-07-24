"""Schemas for realtime token minting and voice orchestration."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.evaluation import NextQuestion


class RealtimeClientSecretRequest(BaseModel):
    lead_id: UUID


class RealtimeClientSecretResponse(BaseModel):
    client_secret: str
    expires_at: int | None = None
    model: str
    voice: str
    session_id: str | None = None


class VoiceContextResponse(BaseModel):
    lead_id: UUID
    known_lead: bool
    display_name: str | None = None
    identity_status: str | None = None
    profile_completed: bool
    progress: int = Field(ge=0, le=100)
    next_question: NextQuestion | None = None
    conversation_opening: str
    confirmed_fields: list[str] = Field(default_factory=list)
    fields_to_confirm: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    demo_mode: bool = True


class VoiceAnswerRequest(BaseModel):
    field: str = Field(min_length=1)
    raw_transcript: str | None = None
    normalized_value: str | int | float | bool | None = None
    action: Literal["answer", "confirm", "correct", "skip"] = "answer"


class VoiceAnswerResponse(BaseModel):
    accepted: bool
    updated_field: str | None = None
    profile_completed: bool = False
    progress: int = 0
    next_question: NextQuestion | None = None
    assistant_guidance: str
    clarification_required: bool = False
    validation_message: str | None = None
    warnings: list[str] = Field(default_factory=list)


class VoiceCompleteResponse(BaseModel):
    completed: bool
    readiness: dict[str, Any]
    recommendations_count: int
    top_project: dict[str, str] | None = None
    next_action: str
    navigation_path: str
    assistant_closing: str
    disclaimer: str
    spoken_summary: str | None = None
    recommended_projects: list[dict[str, Any]] = Field(default_factory=list)
    profile_json_path: str | None = None
    engine: str | None = None


class VoiceEngagementRequest(BaseModel):
    label: Literal[
        "interesado",
        "indeciso",
        "molesto",
        "trolleando",
        "ocupado",
        "desconocido",
    ]
    score: int | None = Field(default=None, ge=0, le=100)
    reason: str | None = Field(default=None, max_length=400)


class VoiceEngagementResponse(BaseModel):
    accepted: bool
    engagement_label: str
    engagement_score: int | None = None
    engagement_reason: str | None = None
    engagement_updated_at: str | None = None
