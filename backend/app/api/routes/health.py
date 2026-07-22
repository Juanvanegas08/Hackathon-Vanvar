"""Health-check endpoints."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.common import HealthResponse

router = APIRouter(tags=["Salud"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Verificar salud del servicio",
    description="Endpoint de salud para monitoreo y verificación rápida del backend.",
    responses={200: {"description": "Servicio disponible"}},
)
def health_check() -> HealthResponse:
    """Return service health status."""
    settings = get_settings()
    return HealthResponse(status="ok", service=settings.app_name)
