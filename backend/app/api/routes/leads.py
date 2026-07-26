"""Lead CRUD and profiling endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import get_lead_service
from app.schemas.evaluation import (
    AdvisorSummaryResponse,
    NextQuestionResponse,
    ReadinessResponse,
)
from app.schemas.lead import LeadCreate, LeadResponse, LeadUpdate
from app.services.lead_service import LeadService

router = APIRouter(prefix="/leads", tags=["Leads"])


@router.post(
    "",
    response_model=LeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear lead",
    description="Crea un nuevo lead con la información inicial disponible.",
)
def create_lead(
    payload: LeadCreate,
    service: LeadService = Depends(get_lead_service),
) -> LeadResponse:
    lead = service.create_lead(payload)
    return LeadResponse.from_lead(lead)


@router.get(
    "",
    response_model=list[LeadResponse],
    summary="Listar leads",
    description="Lista todos los leads almacenados en el repositorio en memoria.",
)
def list_leads(service: LeadService = Depends(get_lead_service)) -> list[LeadResponse]:
    return [LeadResponse.from_lead(lead) for lead in service.list_leads()]


@router.get(
    "/advisor-queue",
    response_model=list[LeadResponse],
    summary="Cola compacta del asesor",
    description=(
        "Lista liviana de leads evaluados para el dashboard del asesor "
        "(una sola consulta SQL)."
    ),
)
def list_advisor_queue(
    service: LeadService = Depends(get_lead_service),
) -> list[LeadResponse]:
    return [LeadResponse.from_lead(lead) for lead in service.list_advisor_queue()]


@router.get(
    "/{lead_id}",
    response_model=LeadResponse,
    summary="Obtener lead",
    description="Consulta un lead por su identificador UUID.",
    responses={404: {"description": "Lead no encontrado"}},
)
def get_lead(
    lead_id: UUID,
    service: LeadService = Depends(get_lead_service),
) -> LeadResponse:
    return LeadResponse.from_lead(service.get_lead(lead_id))


@router.patch(
    "/{lead_id}",
    response_model=LeadResponse,
    summary="Actualizar lead parcialmente",
    description=(
        "Actualiza solo los campos enviados. No elimina información válida "
        "previamente capturada."
    ),
    responses={404: {"description": "Lead no encontrado"}},
)
def update_lead(
    lead_id: UUID,
    payload: LeadUpdate,
    service: LeadService = Depends(get_lead_service),
) -> LeadResponse:
    return LeadResponse.from_lead(service.update_lead(lead_id, payload))


@router.delete(
    "/{lead_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar lead (solo desarrollo)",
    description="Elimina un lead. Pensado únicamente para pruebas y desarrollo.",
    responses={404: {"description": "Lead no encontrado"}},
)
def delete_lead(
    lead_id: UUID,
    service: LeadService = Depends(get_lead_service),
) -> Response:
    service.delete_lead(lead_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{lead_id}/next-question",
    response_model=NextQuestionResponse,
    summary="Obtener siguiente pregunta",
    description=(
        "Devuelve la siguiente pregunta prioritaria según reglas de negocio, "
        "sin usar un LLM."
    ),
    responses={404: {"description": "Lead no encontrado"}},
)
def next_question(
    lead_id: UUID,
    service: LeadService = Depends(get_lead_service),
) -> NextQuestionResponse:
    return service.next_question(lead_id)


@router.post(
    "/{lead_id}/evaluate",
    response_model=ReadinessResponse,
    summary="Evaluar preparación del lead",
    description=(
        "Calcula un puntaje preliminar de preparación/completitud del perfil. "
        "No constituye aprobación crediticia."
    ),
    responses={404: {"description": "Lead no encontrado"}},
)
def evaluate_lead(
    lead_id: UUID,
    service: LeadService = Depends(get_lead_service),
) -> ReadinessResponse:
    return service.evaluate(lead_id)


@router.get(
    "/{lead_id}/summary",
    response_model=AdvisorSummaryResponse,
    summary="Obtener resumen para el asesor",
    description=(
        "Genera un resumen estructurado orientado al futuro asesor comercial. "
        "Usa include_recommendations=false para respuesta rápida cuando las "
        "recomendaciones se cargan por separado."
    ),
    responses={404: {"description": "Lead no encontrado"}},
)
def lead_summary(
    lead_id: UUID,
    include_recommendations: bool = Query(
        default=True,
        description="Si es false, omite el motor de recomendaciones (más rápido).",
    ),
    service: LeadService = Depends(get_lead_service),
) -> AdvisorSummaryResponse:
    return service.summary(
        lead_id,
        include_recommendations=include_recommendations,
    )
