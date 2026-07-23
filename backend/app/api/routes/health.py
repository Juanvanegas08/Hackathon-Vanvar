"""Health-check endpoints."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.common import DatabaseHealthResponse, HealthResponse
from app.services.database_health_service import check_database_health

router = APIRouter(tags=["Salud"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Verificar salud del servicio",
    description="Endpoint de salud para monitoreo y verificación rápida del backend.",
    responses={200: {"description": "Servicio disponible"}},
)
def health_check() -> HealthResponse:
    """Return service health status (independent of PostgreSQL)."""
    settings = get_settings()
    return HealthResponse(status="ok", service=settings.app_name)


@router.get(
    "/health/database",
    response_model=DatabaseHealthResponse,
    summary="Verificar salud de PostgreSQL",
    description=(
        "Comprueba conexión, revisión Alembic, schemas y extensiones. "
        "No revela credenciales ni host completo en producción."
    ),
    responses={200: {"description": "Estado de la base de datos"}},
)
async def database_health_check() -> DatabaseHealthResponse:
    """Return PostgreSQL health without breaking the general /health contract."""
    payload = await check_database_health()
    return DatabaseHealthResponse.model_validate(payload)
