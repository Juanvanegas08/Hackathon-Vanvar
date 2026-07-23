"""Realtime client-secret provider contract."""

from typing import Protocol

from pydantic import BaseModel, Field


class RealtimeClientSecret(BaseModel):
    """Ephemeral browser credential for OpenAI Realtime."""

    client_secret: str = Field(min_length=1)
    expires_at: int | None = None
    model: str
    voice: str
    session_id: str | None = None


class RealtimeClientSecretProvider(Protocol):
    """Provider that mints short-lived Realtime credentials."""

    def create_client_secret(self, *, lead_id: str) -> RealtimeClientSecret:
        """Create an ephemeral client secret for a lead session."""
        ...
