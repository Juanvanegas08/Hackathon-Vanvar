"""Product API for outbound phone calls (now / schedule)."""

from fastapi import APIRouter, Depends

from app.api.deps import get_phone_call_orchestrator
from app.schemas.phone_calls import PhoneCallRequest, PhoneCallResponse
from app.services.phone_call_orchestrator import PhoneCallOrchestrator

router = APIRouter(prefix="/phone", tags=["phone"])


@router.post("/calls", response_model=PhoneCallResponse)
def create_phone_call(
    payload: PhoneCallRequest,
    orchestrator: PhoneCallOrchestrator = Depends(get_phone_call_orchestrator),
) -> PhoneCallResponse:
    """Create or schedule an outbound Laura call for a consented lead."""
    result = orchestrator.request_call(
        phone=payload.phone,
        mode=payload.mode,
        document_type=payload.document_type,
        document_number=payload.document_number,
        data_consent=payload.data_consent,
        scheduled_at=payload.scheduled_at,
    )
    return PhoneCallResponse(**result)
