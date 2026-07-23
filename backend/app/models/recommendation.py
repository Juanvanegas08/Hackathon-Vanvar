"""Recommendation domain models."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.evaluation import ConfidenceLevel


class RecommendationStatus(StrEnum):
    """Outcome of a recommendation request."""

    COMPLETED = "completed"
    INSUFFICIENT_INFORMATION = "insufficient_information"
    NO_MATCHES = "no_matches"
    PROFILES_UNAVAILABLE = "profiles_unavailable"


class MatchedFactor(BaseModel):
    """Explainable contribution of a single scoring criterion."""

    factor: str
    message: str
    contribution: float = Field(ge=0, le=100)


class RegulatoryContext(BaseModel):
    """Commercial/regulatory context related to affiliation quota."""

    affiliation_status: str
    affiliated: bool | None = None
    requires_quota_validation: bool = False
    message: str | None = None


class ProjectRecommendation(BaseModel):
    """Single ranked project recommendation."""

    project_id: str
    project_name: str
    canonical_project_id: str
    rank: int
    compatibility_score: float = Field(ge=0, le=100)
    confidence: ConfidenceLevel
    matched_factors: list[MatchedFactor] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    unavailable_factors: list[str] = Field(default_factory=list)
    brochure_url: str | None = None
    tour_360_url: str | None = None
    municipio: str | None = None
    departamento: str | None = None
    etapa: str | None = None
    historical_profile_available: bool = False
    aliases: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None
    probability: float | None = Field(default=None, ge=0, le=1)
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)


class RecommendationResult(BaseModel):
    """Full recommendation payload for a lead."""

    lead_id: UUID
    recommendation_status: RecommendationStatus
    evaluated_projects: int = 0
    recommended_projects: list[ProjectRecommendation] = Field(default_factory=list)
    profile_completeness: int = Field(default=0, ge=0, le=100)
    overall_confidence: ConfidenceLevel = ConfidenceLevel.LOW
    missing_lead_fields: list[str] = Field(default_factory=list)
    required_fields: list[str] = Field(default_factory=list)
    regulatory_context: RegulatoryContext | None = None
    general_warnings: list[str] = Field(default_factory=list)
    disclaimer: str
    generated_at: datetime
    spoken_summary: str | None = None
    engine: str = "deterministic"
    profile_json_path: str | None = None
