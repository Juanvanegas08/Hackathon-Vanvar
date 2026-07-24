"""Twilio Programmable Voice helpers for Laura phone channel."""

from __future__ import annotations

import logging
from uuid import UUID

from twilio.request_validator import RequestValidator
from twilio.rest import Client
from twilio.twiml.voice_response import Connect, ConversationRelay, VoiceResponse

from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class TwilioCallService:
    """Create outbound calls and build ConversationRelay TwiML."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def _require_ready(self) -> Settings:
        settings = self._settings
        if not settings.is_twilio_ready:
            raise ConfigurationError(
                "Twilio no está configurado. Define TWILIO_ACCOUNT_SID, "
                "TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, TWILIO_PUBLIC_BASE_URL "
                "y OPENAI_API_KEY."
            )
        return settings

    def _client(self) -> Client:
        settings = self._require_ready()
        return Client(settings.twilio_account_sid, settings.twilio_auth_token)

    def public_http_base(self) -> str:
        settings = self._require_ready()
        return str(settings.twilio_public_base_url).rstrip("/")

    def conversation_relay_wss_url(self) -> str:
        base = self.public_http_base()
        if base.startswith("https://"):
            wss = "wss://" + base.removeprefix("https://")
        elif base.startswith("http://"):
            wss = "ws://" + base.removeprefix("http://")
        else:
            wss = f"wss://{base}"
        prefix = self._settings.api_prefix.rstrip("/")
        return f"{wss}{prefix}/twilio/conversation-relay"

    def outbound_webhook_url(self, lead_id: UUID) -> str:
        prefix = self._settings.api_prefix.rstrip("/")
        return f"{self.public_http_base()}{prefix}/twilio/voice/outbound?lead_id={lead_id}"

    def build_conversation_relay_twiml(
        self,
        *,
        lead_id: UUID | None,
        welcome_greeting: str,
        needs_identity: bool = False,
        caller_phone: str | None = None,
    ) -> str:
        """Return TwiML that connects the call to ConversationRelay."""
        response = VoiceResponse()
        connect = Connect()
        relay = ConversationRelay(
            url=self.conversation_relay_wss_url(),
            welcome_greeting=welcome_greeting,
            language="es-MX",
            tts_provider="Google",
            transcription_provider="Google",
        )
        if lead_id is not None:
            relay.parameter(name="lead_id", value=str(lead_id))
        relay.parameter(name="needs_identity", value="true" if needs_identity else "false")
        if caller_phone:
            relay.parameter(name="caller_phone", value=caller_phone)
        connect.append(relay)
        response.append(connect)
        return str(response)

    def start_outbound(self, *, lead_id: UUID, to_phone: str) -> str:
        """Place an outbound call; returns Call SID."""
        settings = self._require_ready()
        client = self._client()
        call = client.calls.create(
            to=to_phone,
            from_=settings.twilio_phone_number,
            url=self.outbound_webhook_url(lead_id),
            method="POST",
        )
        logger.info("Started outbound call %s to %s for lead %s", call.sid, to_phone, lead_id)
        return str(call.sid)

    def validate_request(
        self,
        *,
        url: str,
        params: dict[str, str],
        signature: str | None,
    ) -> bool:
        """Validate Twilio webhook signature when enabled."""
        settings = self._settings
        if not settings.twilio_validate_signature:
            return True
        if not settings.twilio_auth_token:
            return False
        if not signature:
            return False
        validator = RequestValidator(settings.twilio_auth_token)
        return bool(validator.validate(url, params, signature))
