"""Identity lookup and known-lead demo endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_identity_service, get_lead_service, get_settings_dep
from app.core.config import Settings
from app.schemas.identity import (
    ConfirmPrefilledRequest,
    DemoIdentityItem,
    IdentityLookupRequest,
    IdentityLookupResponse,
    LeadFromIdentityRequest,
    LeadFromIdentityResponse,
)
from app.schemas.lead import LeadResponse
from app.services.identity_service import IdentityService
from app.services.lead_service import LeadService

router = APIRouter(tags=["Identidad"])


@router.post(
    "/identity/lookup",
    response_model=IdentityLookupResponse,
    summary="Consultar identidad simulada",
    description=(
        "Busca un documento en el servicio simulado de afiliación. "
        "No crea un lead automáticamente. Solo para demostración."
    ),
)
def lookup_identity(
    payload: IdentityLookupRequest,
    service: IdentityService = Depends(get_identity_service),
) -> IdentityLookupResponse:
    result = service.lookup(payload.document_type, payload.document_number)
    return IdentityLookupResponse.model_validate(result)


@router.post(
    "/leads/from-identity",
    response_model=LeadFromIdentityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear lead desde identidad simulada",
    description=(
        "Crea un lead a partir del mock de afiliación. "
        "Sin consentimiento no se precarga información financiera."
    ),
)
def create_lead_from_identity(
    payload: LeadFromIdentityRequest,
    identity_service: IdentityService = Depends(get_identity_service),
    lead_service: LeadService = Depends(get_lead_service),
) -> LeadFromIdentityResponse:
    lead, context = identity_service.create_lead_from_identity(
        document_type=payload.document_type,
        document_number=payload.document_number,
        data_consent=payload.data_consent,
    )
    next_question = lead_service.next_question(lead.id).next_question
    return LeadFromIdentityResponse(
        lead=LeadResponse.from_lead(lead),
        identity_context=context,
        next_question=next_question,
        demo_mode=True,
    )


@router.post(
    "/leads/{lead_id}/confirm-prefilled-data",
    response_model=LeadResponse,
    summary="Confirmar o corregir datos precargados",
)
def confirm_prefilled_data(
    lead_id: UUID,
    payload: ConfirmPrefilledRequest,
    identity_service: IdentityService = Depends(get_identity_service),
    lead_service: LeadService = Depends(get_lead_service),
) -> LeadResponse:
    lead = lead_service.get_lead(lead_id)
    confirmations = {
        field: item.model_dump() for field, item in payload.confirmations.items()
    }
    updated = identity_service.confirm_prefilled_data(lead, confirmations)
    return LeadResponse.from_lead(updated)


@router.get(
    "/demo/identities",
    response_model=list[DemoIdentityItem],
    summary="Listar identidades ficticias de demostración",
    description="Solo disponible en ambiente development.",
)
def list_demo_identities(
    settings: Settings = Depends(get_settings_dep),
    service: IdentityService = Depends(get_identity_service),
) -> list[DemoIdentityItem]:
    if settings.app_env.lower() not in {"development", "dev", "local", "test"}:
        raise HTTPException(
            status_code=404,
            detail="Endpoint de demostración no disponible en este ambiente",
        )
    return [DemoIdentityItem.model_validate(item) for item in service.list_demo_identities()]
