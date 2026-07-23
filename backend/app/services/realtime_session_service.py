"""Mint ephemeral Realtime credentials for browser sessions."""

from uuid import UUID

from app.providers.openai_realtime_provider import OpenAIRealtimeProvider
from app.providers.realtime_provider import RealtimeClientSecret, RealtimeClientSecretProvider
from app.services.lead_service import LeadService


class RealtimeSessionService:
    """Coordinate Realtime client-secret creation with lead validation."""

    def __init__(
        self,
        lead_service: LeadService,
        provider: RealtimeClientSecretProvider | None = None,
    ) -> None:
        self._leads = lead_service
        self._provider = provider or OpenAIRealtimeProvider()

    def create_client_secret(self, lead_id: UUID) -> RealtimeClientSecret:
        # Ensure the lead exists before minting a secret.
        self._leads.get_lead(lead_id)
        return self._provider.create_client_secret(lead_id=str(lead_id))
