"""OpenAI Realtime ephemeral client-secret provider."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError, RealtimeServiceError
from app.providers.realtime_provider import RealtimeClientSecret

logger = logging.getLogger(__name__)

OPENAI_CLIENT_SECRETS_URL = "https://api.openai.com/v1/realtime/client_secrets"


class OpenAIRealtimeProvider:
    """Mint ephemeral Realtime credentials using the server-side API key."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._http_client = http_client

    def create_client_secret(self, *, lead_id: str) -> RealtimeClientSecret:
        if not self._settings.openai_realtime_enabled:
            raise ConfigurationError("OpenAI Realtime está deshabilitado en este ambiente.")
        api_key = self._settings.openai_api_key
        if not api_key:
            raise ConfigurationError(
                "OPENAI_API_KEY no está configurada. "
                "Configura la clave en el servidor antes de iniciar voz."
            )

        payload = {
            "session": {
                "type": "realtime",
                "model": self._settings.openai_realtime_model,
                "audio": {
                    "output": {"voice": self._settings.openai_realtime_voice},
                    "input": {
                        "transcription": {
                            "model": self._settings.openai_realtime_transcription_model,
                        }
                    },
                },
                "metadata": {"lead_id": lead_id, "product": "casalista_voice"},
            }
        }

        try:
            response = self._request(api_key=api_key, payload=payload)
        except httpx.TimeoutException as exc:
            logger.warning("OpenAI Realtime timeout while minting client secret")
            raise RealtimeServiceError(
                "No fue posible iniciar la conversación de voz.",
                code="realtime_timeout",
            ) from exc
        except httpx.HTTPError as exc:
            logger.warning("OpenAI Realtime transport error while minting client secret")
            raise RealtimeServiceError(
                "No fue posible iniciar la conversación de voz.",
                code="realtime_service_unavailable",
            ) from exc

        if response.status_code in {401, 403}:
            raise RealtimeServiceError(
                "No fue posible autenticar el servicio de voz.",
                code="realtime_unauthorized",
            )
        if response.status_code == 429:
            raise RealtimeServiceError(
                "El servicio de voz alcanzó su límite temporal. Intenta más tarde.",
                code="realtime_rate_limited",
            )
        if response.status_code >= 500:
            raise RealtimeServiceError(
                "No fue posible iniciar la conversación de voz.",
                code="realtime_upstream_error",
            )
        if response.status_code >= 400:
            raise RealtimeServiceError(
                "No fue posible iniciar la conversación de voz.",
                code="realtime_service_unavailable",
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise RealtimeServiceError(
                "No fue posible iniciar la conversación de voz.",
                code="realtime_invalid_response",
            ) from exc

        secret = self._extract_secret(data)
        if not secret:
            raise RealtimeServiceError(
                "No fue posible iniciar la conversación de voz.",
                code="realtime_invalid_response",
            )

        expires_at = self._extract_expires_at(data)
        session_id = None
        session = data.get("session")
        if isinstance(session, dict):
            raw_id = session.get("id")
            session_id = str(raw_id) if raw_id else None

        return RealtimeClientSecret(
            client_secret=secret,
            expires_at=expires_at,
            model=self._settings.openai_realtime_model,
            voice=self._settings.openai_realtime_voice,
            session_id=session_id,
        )

    def _request(self, *, api_key: str, payload: dict[str, Any]) -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        timeout = self._settings.openai_request_timeout_seconds
        if self._http_client is not None:
            return self._http_client.post(
                OPENAI_CLIENT_SECRETS_URL,
                headers=headers,
                json=payload,
                timeout=timeout,
            )
        with httpx.Client(timeout=timeout) as client:
            return client.post(
                OPENAI_CLIENT_SECRETS_URL,
                headers=headers,
                json=payload,
            )

    @staticmethod
    def _extract_secret(data: dict[str, Any]) -> str | None:
        value = data.get("value")
        if isinstance(value, str) and value.strip():
            return value.strip()
        client_secret = data.get("client_secret")
        if isinstance(client_secret, str) and client_secret.strip():
            return client_secret.strip()
        if isinstance(client_secret, dict):
            nested = client_secret.get("value")
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
        return None

    @staticmethod
    def _extract_expires_at(data: dict[str, Any]) -> int | None:
        expires_at = data.get("expires_at")
        if isinstance(expires_at, int):
            return expires_at
        client_secret = data.get("client_secret")
        if isinstance(client_secret, dict):
            nested = client_secret.get("expires_at")
            if isinstance(nested, int):
                return nested
        return None
