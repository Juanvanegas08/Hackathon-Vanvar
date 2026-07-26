"""Server-side OpenAI Realtime WebSocket session for phone (text out → Twilio TTS)."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection

from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime"

ToolExecutor = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


class PhoneRealtimeSession:
    """One OpenAI Realtime connection per phone call (text modality + tools)."""

    def __init__(
        self,
        *,
        instructions: str,
        tools: list[dict[str, Any]],
        tool_executor: ToolExecutor,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._instructions = instructions
        self._tools = tools
        self._tool_executor = tool_executor
        self._ws: ClientConnection | None = None
        self._recv_task: asyncio.Task[None] | None = None
        self._events: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._closed = False
        self._response_active = False
        self._cancel_requested = False

    @property
    def connected(self) -> bool:
        return self._ws is not None and not self._closed

    @property
    def response_active(self) -> bool:
        return self._response_active

    async def connect(self) -> None:
        if self.connected:
            return
        key = self._settings.openai_api_key
        if not key:
            raise ConfigurationError("OPENAI_API_KEY no configurada")
        model = self._settings.openai_realtime_model
        url = f"{OPENAI_REALTIME_URL}?model={model}"
        # GA Realtime: Authorization only (no OpenAI-Beta header — beta is disabled).
        try:
            self._ws = await websockets.connect(
                url,
                additional_headers={
                    "Authorization": f"Bearer {key}",
                },
                max_size=8 * 1024 * 1024,
                ping_interval=20,
                ping_timeout=20,
            )
            self._closed = False
            self._response_active = False
            self._cancel_requested = False
            self._recv_task = asyncio.create_task(self._recv_loop())
            await self._wait_for_types({"session.created"}, timeout=15.0)
            await self._send(
                {
                    "type": "session.update",
                    "session": {
                        "type": "realtime",
                        "model": model,
                        "instructions": self._instructions,
                        "output_modalities": ["text"],
                        "tools": self._tools,
                        "tool_choice": "auto",
                    },
                }
            )
            await self._wait_for_types({"session.updated"}, timeout=15.0)
        except Exception:
            await self.close()
            raise
        logger.info("Phone Realtime session ready model=%s", model)

    async def close(self) -> None:
        self._closed = True
        self._response_active = False
        self._cancel_requested = False
        if self._recv_task is not None:
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass
            self._recv_task = None
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:  # noqa: BLE001
                logger.debug("Realtime WS close failed", exc_info=True)
            self._ws = None

    async def cancel_response(self) -> None:
        """Cancel only if OpenAI is generating; ignore otherwise."""
        if not self.connected:
            return
        self._cancel_requested = True
        if not self._response_active:
            return
        try:
            await self._send({"type": "response.cancel"})
        except Exception:  # noqa: BLE001
            logger.debug("response.cancel failed", exc_info=True)

    @staticmethod
    def _is_benign_cancel_error(error: Any) -> bool:
        if not isinstance(error, dict):
            return False
        code = str(error.get("code") or "")
        message = str(error.get("message") or "").lower()
        return code == "response_cancel_not_active" or (
            "no active response" in message
        )

    async def run_turn(
        self,
        user_text: str,
        *,
        allow_tools: bool = True,
    ) -> AsyncIterator[str]:
        """Send user text, handle tools, yield spoken text deltas."""
        await self.connect()
        text = (user_text or "").strip()
        if not text:
            yield "No te escuche bien. Me lo repites, por favor?"
            return

        self._cancel_requested = False
        await self._drain_events()
        await self._send(
            {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": text}],
                },
            }
        )

        for round_idx in range(12):
            if self._cancel_requested:
                return
            self._response_active = True
            response_payload: dict[str, Any] = {
                "output_modalities": ["text"],
            }
            # Kickoff: force speech first (no tool round-trip before TTS).
            if not allow_tools and round_idx == 0:
                response_payload["tool_choice"] = "none"
            await self._send(
                {
                    "type": "response.create",
                    "response": response_payload,
                }
            )
            spoken_any = False
            function_calls: list[dict[str, Any]] = []
            cancelled = False
            async for kind, payload in self._iter_response_events():
                if kind == "text_delta":
                    spoken_any = True
                    yield str(payload)
                elif kind == "function_calls":
                    function_calls = list(payload)
                elif kind == "cancelled":
                    cancelled = True
                elif kind == "error":
                    if self._is_benign_cancel_error(payload):
                        logger.debug("Ignoring benign Realtime cancel error: %s", payload)
                        continue
                    logger.error("Realtime turn error: %s", payload)
                    if not spoken_any and not self._cancel_requested:
                        yield "Disculpa, tuve un problema. Me lo repites?"
                    return

            self._response_active = False
            if cancelled or self._cancel_requested:
                # Interrupt/cancel: silencio; el siguiente prompt de Twilio sigue.
                return

            if function_calls and allow_tools:
                for call in function_calls:
                    if self._cancel_requested:
                        return
                    name = str(call.get("name") or "")
                    call_id = str(call.get("call_id") or "")
                    raw_args = call.get("arguments") or "{}"
                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else {}
                    except json.JSONDecodeError:
                        args = {}
                    if not isinstance(args, dict):
                        args = {}
                    result = await self._tool_executor(name, args)
                    await self._send(
                        {
                            "type": "conversation.item.create",
                            "item": {
                                "type": "function_call_output",
                                "call_id": call_id,
                                "output": json.dumps(
                                    result, ensure_ascii=False, default=str
                                ),
                            },
                        }
                    )
                continue

            if not spoken_any:
                # Evitar bucle de disculpas: un empujón corto, no "me lo repites".
                yield "¿Me repites eso, por favor?"
            return

        yield "Un segundo, estoy organizando tu informacion. Seguimos?"

    async def _recv_loop(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                if self._closed:
                    break
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, dict):
                    continue
                # No ensuciar el turno con cancels que ya no aplican.
                if str(event.get("type") or "") == "error":
                    err = event.get("error") or event
                    if self._is_benign_cancel_error(err):
                        logger.debug("Dropping benign cancel error: %s", err)
                        self._response_active = False
                        continue
                await self._events.put(event)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Realtime recv loop ended")
            await self._events.put({"type": "error", "error": {"message": "ws_closed"}})

    async def _send(self, payload: dict[str, Any]) -> None:
        if self._ws is None:
            raise ConfigurationError("Sesión Realtime no conectada")
        await self._ws.send(json.dumps(payload))

    async def _drain_events(self) -> None:
        while True:
            try:
                self._events.get_nowait()
            except asyncio.QueueEmpty:
                return

    async def _wait_for_types(
        self,
        types: set[str],
        *,
        timeout: float,
    ) -> dict[str, Any]:
        deadline = asyncio.get_running_loop().time() + timeout
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise ConfigurationError(f"Timeout esperando {types}")
            event = await asyncio.wait_for(self._events.get(), timeout=remaining)
            etype = str(event.get("type") or "")
            if etype == "error":
                err = event.get("error") or event
                if self._is_benign_cancel_error(err):
                    continue
                raise ConfigurationError(
                    f"OpenAI Realtime error: {err}"
                )
            if etype in types:
                return event

    async def _iter_response_events(
        self,
    ) -> AsyncIterator[tuple[str, Any]]:
        """Yield text deltas, then function_calls / cancelled / error."""
        function_calls: list[dict[str, Any]] = []
        while True:
            event = await self._events.get()
            etype = str(event.get("type") or "")

            if etype in {
                "response.created",
                "response.output_item.added",
                "response.content_part.added",
                "response.content_part.done",
                "response.output_item.done",
                "rate_limits.updated",
            }:
                continue

            if etype in {"response.output_text.delta", "response.text.delta"}:
                delta = event.get("delta")
                if delta:
                    yield ("text_delta", str(delta))
                continue

            if etype == "response.function_call_arguments.done":
                continue

            if etype == "response.done":
                self._response_active = False
                response = event.get("response") or {}
                output = response.get("output") or []
                for item in output:
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") == "function_call":
                        function_calls.append(
                            {
                                "name": item.get("name"),
                                "call_id": item.get("call_id"),
                                "arguments": item.get("arguments") or "{}",
                            }
                        )
                yield ("function_calls", function_calls)
                return

            if etype == "error":
                err = event.get("error") or event
                if self._is_benign_cancel_error(err):
                    self._response_active = False
                    logger.debug("Ignoring benign cancel in turn loop: %s", err)
                    continue
                self._response_active = False
                yield ("error", err)
                return

            if etype == "response.cancelled":
                self._response_active = False
                yield ("cancelled", None)
                return
