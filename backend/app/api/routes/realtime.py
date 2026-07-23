"""Realtime ephemeral client-secret routes."""

from fastapi import APIRouter, Depends

from app.api.deps import get_realtime_session_service
from app.schemas.realtime import RealtimeClientSecretRequest, RealtimeClientSecretResponse
from app.services.realtime_session_service import RealtimeSessionService

router = APIRouter(tags=["Realtime"])


@router.post(
    "/realtime/client-secret",
    response_model=RealtimeClientSecretResponse,
    summary="Crear token efímero para OpenAI Realtime",
    description=(
        "Usa la API key del servidor para mintar un client secret de corta duración. "
        "Nunca expone OPENAI_API_KEY al navegador."
    ),
)
def create_realtime_client_secret(
    payload: RealtimeClientSecretRequest,
    service: RealtimeSessionService = Depends(get_realtime_session_service),
) -> RealtimeClientSecretResponse:
    result = service.create_client_secret(payload.lead_id)
    return RealtimeClientSecretResponse.model_validate(result.model_dump())
