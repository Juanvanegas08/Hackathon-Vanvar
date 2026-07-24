"""Identity lookup and known-lead demo endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

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
    summary="Consultar identidad por documento",
    description=(
        "Busca primero en la base de datos por hash de documento. "
        "Si no existe, consulta el servicio simulado de afiliación. "
        "No crea un lead automáticamente."
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
    summary="Obtener o crear lead desde identificación",
    description=(
        "Si el documento ya existe en BD y data_consent=true, recupera el perfil. "
        "Si data_consent=false sobre un perfil existente, reinicia desde cero "
        "(borra datos de conversación, predisposición y recomendaciones). "
        "Si no existe, crea el lead (mock de afiliación cuando aplique). "
        "Sin consentimiento en alta nueva no se precarga información financiera."
    ),
)
def create_lead_from_identity(
    payload: LeadFromIdentityRequest,
    response: Response,
    identity_service: IdentityService = Depends(get_identity_service),
    lead_service: LeadService = Depends(get_lead_service),
) -> LeadFromIdentityResponse:
    lead, context = identity_service.create_lead_from_identity(
        document_type=payload.document_type,
        document_number=payload.document_number,
        data_consent=payload.data_consent,
    )
    created = bool(context.get("created", True))
    response.status_code = (
        status.HTTP_201_CREATED if created else status.HTTP_200_OK
    )
    next_question = lead_service.next_question(lead.id).next_question
    return LeadFromIdentityResponse(
        lead=LeadResponse.from_lead(lead),
        identity_context=context,
        next_question=next_question,
        demo_mode=bool(context.get("demo_mode", True)),
        created=created,
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
