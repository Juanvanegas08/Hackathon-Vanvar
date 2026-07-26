"""Voice orchestration routes for the realtime agent tools."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_voice_orchestration_service
from app.schemas.realtime import (
    VoiceAnswerRequest,
    VoiceAnswerResponse,
    VoiceCompleteRequest,
    VoiceCompleteResponse,
    VoiceContextResponse,
    VoiceEngagementRequest,
    VoiceEngagementResponse,
)
from app.services.voice_orchestration_service import VoiceOrchestrationService

router = APIRouter(prefix="/voice", tags=["Voz"])


@router.get(
    "/leads/{lead_id}/context",
    response_model=VoiceContextResponse,
    summary="Contexto compacto para el agente de voz",
)
def get_voice_context(
    lead_id: UUID,
    service: VoiceOrchestrationService = Depends(get_voice_orchestration_service),
) -> VoiceContextResponse:
    return service.get_context(lead_id)


@router.post(
    "/leads/{lead_id}/answer",
    response_model=VoiceAnswerResponse,
    summary="Registrar respuesta de voz validada",
)
def submit_voice_answer(
    lead_id: UUID,
    payload: VoiceAnswerRequest,
    service: VoiceOrchestrationService = Depends(get_voice_orchestration_service),
) -> VoiceAnswerResponse:
    return service.submit_answer(lead_id, payload)


@router.post(
    "/leads/{lead_id}/engagement",
    response_model=VoiceEngagementResponse,
    summary="Registrar predisposición/sentimiento detectado en voz",
)
def report_voice_engagement(
    lead_id: UUID,
    payload: VoiceEngagementRequest,
    service: VoiceOrchestrationService = Depends(get_voice_orchestration_service),
) -> VoiceEngagementResponse:
    return service.report_engagement(lead_id, payload)


@router.post(
    "/leads/{lead_id}/complete",
    response_model=VoiceCompleteResponse,
    summary="Finalizar perfilamiento por voz",
)
def complete_voice_profile(
    lead_id: UUID,
    payload: VoiceCompleteRequest | None = None,
    service: VoiceOrchestrationService = Depends(get_voice_orchestration_service),
) -> VoiceCompleteResponse:
    return service.complete(lead_id, payload)
