"""Twilio Programmable Voice helpers for Laura phone channel."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from twilio.request_validator import RequestValidator
from twilio.rest import Client
from twilio.twiml.voice_response import Connect, ConversationRelay, Gather, VoiceResponse

from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


def sanitize_elevenlabs_voice(voice: str | None) -> str:
    """Normalize ElevenLabs voice for ConversationRelay.

    Keeps model/speed suffixes Twilio accepts (e.g. ``id-flash_v2_5`` or
    ``id-1.2_0.6_0.8``). Only strips clearly invalid trailing junk.
    """
    raw = (voice or "").strip()
    if not raw:
        return ""
    # Allow: voiceId, voiceId-model, voiceId-speed_stability_similarity
    # Reject accidental query strings / spaces.
    cleaned = raw.split("?", 1)[0].split("#", 1)[0].strip()
    if " " in cleaned:
        cleaned = cleaned.split(" ", 1)[0]
    return cleaned


class TwilioCallService:
    """Create outbound calls and build voice TwiML."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def _require_ready(self) -> Settings:
        settings = self._settings
        missing: list[str] = []
        if not settings.twilio_account_sid:
            missing.append("TWILIO_ACCOUNT_SID")
        if not settings.twilio_auth_token:
            missing.append("TWILIO_AUTH_TOKEN")
        if not settings.twilio_phone_number:
            missing.append("TWILIO_PHONE_NUMBER")
        if not (settings.twilio_public_base_url or "").strip():
            missing.append("TWILIO_PUBLIC_BASE_URL")
        if not settings.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if missing:
            raise ConfigurationError(
                "Twilio no está listo. Falta configurar: "
                + ", ".join(missing)
                + ". En local usa un tunnel (ngrok) y pon la URL HTTPS en TWILIO_PUBLIC_BASE_URL."
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

    def connect_action_url(self) -> str:
        prefix = self._settings.api_prefix.rstrip("/")
        return f"{self.public_http_base()}{prefix}/twilio/voice/connect-status"

    def turn_webhook_url(
        self,
        *,
        lead_id: UUID | None = None,
        needs_identity: bool = False,
    ) -> str:
        prefix = self._settings.api_prefix.rstrip("/")
        url = f"{self.public_http_base()}{prefix}/twilio/voice/turn"
        params: list[str] = []
        if lead_id is not None:
            params.append(f"lead_id={lead_id}")
        if needs_identity:
            params.append("needs_identity=true")
        if params:
            return f"{url}?{'&'.join(params)}"
        return url

    def build_voice_twiml(
        self,
        *,
        lead_id: UUID | None,
        welcome_greeting: str,
        needs_identity: bool = False,
        caller_phone: str | None = None,
        prompt_after_reply: str | None = None,
    ) -> str:
        """Build TwiML according to TWILIO_VOICE_MODE."""
        mode = (self._settings.twilio_voice_mode or "gather").strip().lower()
        if mode == "conversation_relay":
            return self.build_conversation_relay_twiml(
                lead_id=lead_id,
                welcome_greeting=welcome_greeting,
                needs_identity=needs_identity,
                caller_phone=caller_phone,
            )
        # Gather cannot match web Realtime; keep a minimal prompt if greeting empty.
        say = (prompt_after_reply or welcome_greeting or "").strip() or (
            "Hola, soy Laura de Colsubsidio. Te escucho."
        )
        return self.build_gather_twiml(
            lead_id=lead_id,
            say_text=say,
            needs_identity=needs_identity,
        )

    def build_gather_twiml(
        self,
        *,
        lead_id: UUID | None,
        say_text: str,
        needs_identity: bool = False,
    ) -> str:
        """Speech Gather loop — works without ConversationRelay onboarding."""
        response = VoiceResponse()
        action = self.turn_webhook_url(
            lead_id=lead_id,
            needs_identity=needs_identity,
        )
        gather = Gather(
            input="speech",
            language="es-MX",
            speech_timeout="auto",
            action=action,
            method="POST",
            timeout=8,
        )
        # Keep Say simple: language only (avoids Polly voice mismatch errors).
        gather.say(say_text, language="es-MX")
        response.append(gather)
        response.say(
            "No te escuche bien. Vamos a intentarlo otra vez.",
            language="es-MX",
        )
        response.redirect(action, method="POST")
        return str(response)

    def build_conversation_relay_twiml(
        self,
        *,
        lead_id: UUID | None,
        welcome_greeting: str,
        needs_identity: bool = False,
        caller_phone: str | None = None,
    ) -> str:
        """ConversationRelay TwiML with barge-in (requires AI/ML addendum)."""
        settings = self._settings
        response = VoiceResponse()
        connect = Connect(action=self.connect_action_url(), method="POST")
        # Instant audio via welcomeGreeting; Realtime kickoff continues in parallel.
        speech_timeout = settings.twilio_speech_timeout_ms
        tts_provider = (settings.twilio_tts_provider or "ElevenLabs").strip()
        tts_voice = settings.twilio_tts_voice or ""
        if tts_provider.lower() == "elevenlabs":
            tts_voice = sanitize_elevenlabs_voice(tts_voice)
        relay_kwargs: dict[str, Any] = {
            "url": self.conversation_relay_wss_url(),
            "language": "es-US",
            "tts_provider": tts_provider,
            "voice": tts_voice or settings.twilio_tts_voice,
            "transcription_provider": (
                settings.twilio_transcription_provider or "Deepgram"
            ),
            "speech_model": settings.twilio_speech_model or "nova-2-general",
            "speech_timeout": str(speech_timeout),
            "interruptible": "speech",
            "interrupt_sensitivity": "medium",
            "ignore_backchannel": True,
        }
        if tts_provider.lower() == "elevenlabs":
            relay_kwargs["elevenlabs_text_normalization"] = "on"
        greeting = (welcome_greeting or "").strip()
        if greeting:
            relay_kwargs["welcome_greeting"] = greeting
            relay_kwargs["welcome_greeting_interruptible"] = "any"
        relay = ConversationRelay(**relay_kwargs)
        if lead_id is not None:
            relay.parameter(name="lead_id", value=str(lead_id))
        relay.parameter(name="needs_identity", value="true" if needs_identity else "false")
        if caller_phone:
            relay.parameter(name="caller_phone", value=caller_phone)
        connect.append(relay)
        response.append(connect)
        response.say(
            "Tuve un problema tecnico al conectar la conversacion. "
            "Por favor intenta de nuevo en un momento.",
            language="es-US",
        )
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
