"""Product API for outbound phone calls (now / schedule)."""

from fastapi import APIRouter, Depends

from app.api.deps import get_phone_call_orchestrator
from app.schemas.phone_calls import (
    PhoneCallRequest,
    PhoneCallResponse,
    PhoneLookupRequest,
    PhoneLookupResponse,
)
from app.services.phone_call_orchestrator import PhoneCallOrchestrator

router = APIRouter(prefix="/phone", tags=["phone"])


@router.post("/lookup", response_model=PhoneLookupResponse)
def lookup_phone_identity(
    payload: PhoneLookupRequest,
    orchestrator: PhoneCallOrchestrator = Depends(get_phone_call_orchestrator),
) -> PhoneLookupResponse:
    """Lookup a document before starting a call (known phone last-4 vs new lead)."""
    result = orchestrator.lookup_for_call(
        document_type=payload.document_type,
        document_number=payload.document_number,
    )
    return PhoneLookupResponse(**result)


@router.post("/calls", response_model=PhoneCallResponse)
def create_phone_call(
    payload: PhoneCallRequest,
    orchestrator: PhoneCallOrchestrator = Depends(get_phone_call_orchestrator),
) -> PhoneCallResponse:
    """Create or schedule an outbound Laura call for a consented lead."""
    result = orchestrator.request_call(
        phone=payload.phone,
        country_code=payload.country_code,
        nombre=payload.nombre,
        mode=payload.mode,
        document_type=payload.document_type,
        document_number=payload.document_number,
        data_consent=payload.data_consent,
        confirm_stored_phone=payload.confirm_stored_phone,
        scheduled_at=payload.scheduled_at,
    )
    return PhoneCallResponse(**result)
