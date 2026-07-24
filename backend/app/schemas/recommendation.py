"""Recommendation and project listing API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.evaluation import ConfidenceLevel
from app.models.project import HistoricalProfile
from app.models.recommendation import (
    MatchedFactor,
    ProjectRecommendation,
    RecommendationStatus,
    RegulatoryContext,
)


class ProjectResponse(BaseModel):
    """Project catalog item exposed by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nombre: str
    codigo: str | None = None
    etapa: str | None = None
    ubicacion: str | None = None
    municipio: str | None = None
    departamento: str | None = None
    valor_minimo: float | None = None
    valor_maximo: float | None = None
    brochure_url: str | None = None
    recorrido_360_url: str | None = None
    disponible: bool = True
    perfil_historico: HistoricalProfile


class RecommendationResponse(BaseModel):
    """API response for lead recommendations."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "lead_id": "00000000-0000-0000-0000-000000000001",
                    "recommendation_status": "completed",
                    "evaluated_projects": 20,
                    "recommended_projects": [],
                    "profile_completeness": 82,
                    "overall_confidence": "medium",
                    "missing_lead_fields": ["situacion_crediticia"],
                    "required_fields": [],
                    "regulatory_context": {
                        "affiliation_status": "affiliated",
                        "affiliated": True,
                        "requires_quota_validation": False,
                        "message": (
                            "Lead afiliado: factor favorable para el objetivo "
                            "regulatorio 90/10."
                        ),
                    },
                    "general_warnings": [],
                    "disclaimer": (
                        "Las recomendaciones son orientativas y no constituyen "
                        "aprobación de crédito ni garantía de disponibilidad."
                    ),
                    "generated_at": "2026-07-22T00:00:00Z",
                }
            ]
        }
    )

    lead_id: UUID
    recommendation_status: RecommendationStatus
    evaluated_projects: int
    recommended_projects: list[ProjectRecommendation]
    profile_completeness: int
    overall_confidence: ConfidenceLevel
    missing_lead_fields: list[str] = Field(default_factory=list)
    required_fields: list[str] = Field(default_factory=list)
    regulatory_context: RegulatoryContext | None = None
    general_warnings: list[str] = Field(default_factory=list)
    disclaimer: str
    generated_at: datetime
    spoken_summary: str | None = None
    engine: str = "deterministic"
    profile_json_path: str | None = None


# Re-export for convenience in OpenAPI examples.
__all__ = [
    "MatchedFactor",
    "ProjectRecommendation",
    "ProjectResponse",
    "RecommendationResponse",
    "RegulatoryContext",
]
