"""Recommendation endpoints for leads."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_lead_service, get_recommendation_service
from app.schemas.recommendation import RecommendationResponse
from app.services.lead_service import LeadService
from app.services.recommendation_service import RecommendationService

router = APIRouter(tags=["Recomendaciones"])


@router.get(
    "/leads/{lead_id}/recommendations",
    response_model=RecommendationResponse,
    summary="Recomendar proyectos para un lead",
    description=(
        "Devuelve hasta N proyectos compatibles con explicación de puntaje. "
        "No predice compra ni aprueba crédito."
    ),
    responses={404: {"description": "Lead no encontrado"}},
)
def recommend_projects_for_lead(
    lead_id: UUID,
    limit: int = Query(default=3, ge=1, le=10, description="Máximo de recomendaciones"),
    include_unavailable: bool = Query(
        default=False,
        description="Incluir proyectos marcados como no disponibles",
    ),
    min_score: float | None = Query(
        default=None,
        ge=0,
        le=100,
        description="Puntaje mínimo de compatibilidad",
    ),
    prefer_openai: bool | None = Query(
        default=None,
        description=(
            "Si es false, usa el motor determinístico (más rápido). "
            "Si es null, respeta la configuración del servidor."
        ),
    ),
    lead_service: LeadService = Depends(get_lead_service),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationResponse:
    lead = lead_service.get_lead(lead_id)
    result = recommendation_service.recommend_for_lead(
        lead,
        limit=limit,
        include_unavailable=include_unavailable,
        min_score=min_score,
        prefer_openai=prefer_openai,
    )
    if result.recommended_projects:
        try:
            lead_service.apply_commercial_from_recommendations(lead_id, result)
        except Exception:  # noqa: BLE001
            pass
    return RecommendationResponse.model_validate(result.model_dump())
