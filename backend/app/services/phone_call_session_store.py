"""In-memory PhoneLauraAgent sessions keyed by Twilio CallSid."""

from __future__ import annotations

from threading import Lock
from uuid import UUID

from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.services.identity_service import IdentityService
from app.services.lead_service import LeadService
from app.services.phone_laura_agent import PhoneLauraAgent
from app.services.voice_orchestration_service import VoiceOrchestrationService


class PhoneCallSessionStore:
    """Process-local agent sessions for Gather-based phone calls."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._agents: dict[str, PhoneLauraAgent] = {}

    def get_or_create(
        self,
        *,
        call_sid: str,
        voice: VoiceOrchestrationService,
        lead_service: LeadService,
        identity_service: IdentityService,
        settings: Settings,
        lead_id: UUID | None,
        caller_phone: str | None,
        needs_identity: bool,
    ) -> PhoneLauraAgent:
        with self._lock:
            existing = self._agents.get(call_sid)
            if existing is not None:
                if lead_id is not None and existing.lead_id is None:
                    existing.lead_id = lead_id
                    existing.needs_identity = False
                return existing
            display_name = None
            if lead_id is not None:
                try:
                    display_name = (
                        (lead_service.get_lead(lead_id).nombre or "").strip() or None
                    )
                except NotFoundError:
                    display_name = None
            agent = PhoneLauraAgent(
                voice=voice,
                lead_service=lead_service,
                identity_service=identity_service,
                settings=settings,
                lead_id=lead_id,
                caller_phone=caller_phone,
                needs_identity=needs_identity or lead_id is None,
                display_name=display_name,
            )
            self._agents[call_sid] = agent
            return agent

    def drop(self, call_sid: str) -> None:
        with self._lock:
            self._agents.pop(call_sid, None)
