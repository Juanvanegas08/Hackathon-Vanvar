"""Phone Realtime session parity with web Laura agent."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.core.config import Settings
from app.services.phone_laura_agent import PhoneLauraAgent
from app.services.phone_realtime_session import PhoneRealtimeSession
from app.services.twilio_call_service import TwilioCallService, sanitize_elevenlabs_voice


@pytest.mark.asyncio
async def test_realtime_session_run_turn_tool_then_text() -> None:
    settings = Settings(
        OPENAI_API_KEY="sk-test",
        OPENAI_REALTIME_MODEL="gpt-realtime-2.1",
        PERSISTENCE_PROVIDER="memory",
        DATABASE_ENABLED=False,
    )
    tool_calls: list[str] = []

    async def executor(name: str, args: dict[str, Any]) -> dict[str, Any]:
        tool_calls.append(name)
        return {"ok": True}

    session = PhoneRealtimeSession(
        instructions="Eres Laura.",
        tools=[
            {
                "type": "function",
                "name": "get_voice_context",
                "description": "ctx",
                "parameters": {"type": "object", "properties": {}},
            }
        ],
        tool_executor=executor,
        settings=settings,
    )

    class FakeWS:
        def __init__(self) -> None:
            self.sent: list[dict[str, Any]] = []

        async def send(self, raw: str) -> None:
            self.sent.append(json.loads(raw))

        async def close(self) -> None:
            return None

    fake = FakeWS()
    session._ws = fake  # noqa: SLF001
    session._closed = False
    session._recv_task = asyncio.create_task(asyncio.sleep(3600))  # noqa: SLF001

    async def enqueue_turn_events() -> None:
        # Give run_turn time to send response.create
        await asyncio.sleep(0.01)
        await session._events.put(  # noqa: SLF001
            {
                "type": "response.done",
                "response": {
                    "output": [
                        {
                            "type": "function_call",
                            "name": "get_voice_context",
                            "call_id": "call_1",
                            "arguments": "{}",
                        }
                    ]
                },
            }
        )
        await asyncio.sleep(0.01)
        await session._events.put(
            {"type": "response.output_text.delta", "delta": "Hola, "}
        )  # noqa: SLF001
        await session._events.put(
            {"type": "response.output_text.delta", "delta": "soy Laura."}
        )  # noqa: SLF001
        await session._events.put(
            {"type": "response.done", "response": {"output": []}}
        )  # noqa: SLF001

    feeder = asyncio.create_task(enqueue_turn_events())
    parts: list[str] = []
    async for chunk in session.run_turn("hola"):
        parts.append(chunk)
    await feeder
    await session.close()

    assert tool_calls == ["get_voice_context"]
    assert "".join(parts) == "Hola, soy Laura."
    assert any(
        item.get("type") == "conversation.item.create"
        and (item.get("item") or {}).get("type") == "function_call_output"
        for item in fake.sent
    )


def test_phone_agent_active_tools_include_web_set() -> None:
    agent = PhoneLauraAgent(
        voice=MagicMock(),
        lead_service=MagicMock(),
        identity_service=MagicMock(),
        settings=Settings(
            OPENAI_API_KEY="sk-test",
            PERSISTENCE_PROVIDER="memory",
            DATABASE_ENABLED=False,
        ),
        lead_id=uuid4(),
        needs_identity=False,
    )
    names = {t["name"] for t in agent._active_tools()}  # noqa: SLF001
    assert {
        "get_voice_context",
        "submit_current_answer",
        "report_user_engagement",
        "complete_voice_profile",
        "end_call",
    } <= names
    assert "resolve_identity" not in names

    agent.needs_identity = True
    names2 = {t["name"] for t in agent._active_tools()}  # noqa: SLF001
    assert "resolve_identity" in names2


def test_conversation_relay_twiml_elevenlabs_sanitized_voice() -> None:
    settings = Settings(
        TWILIO_ACCOUNT_SID="ACffffffffffffffffffffffffffffffff",
        TWILIO_AUTH_TOKEN="test_auth_token_1234567890",
        TWILIO_PHONE_NUMBER="+13203857702",
        TWILIO_PUBLIC_BASE_URL="https://example.test",
        TWILIO_VALIDATE_SIGNATURE=False,
        TWILIO_VOICE_MODE="conversation_relay",
        TWILIO_TTS_PROVIDER="ElevenLabs",
        TWILIO_TTS_VOICE="b2htR0pMe28pYwCY9gnP-flash_v2_5-1.05",
        TWILIO_TRANSCRIPTION_PROVIDER="Deepgram",
        OPENAI_API_KEY="sk-test",
        PERSISTENCE_PROVIDER="memory",
        DATABASE_ENABLED=False,
    )
    xml = TwilioCallService(settings=settings).build_conversation_relay_twiml(
        lead_id=uuid4(),
        welcome_greeting="",
        needs_identity=False,
    )
    assert "ConversationRelay" in xml
    assert 'ttsProvider="ElevenLabs"' in xml
    assert "b2htR0pMe28pYwCY9gnP-flash_v2_5-1.05" in xml
    assert 'language="es-US"' in xml
    assert 'elevenlabsTextNormalization="on"' in xml
    assert "welcomeGreeting=" not in xml
    assert (
        sanitize_elevenlabs_voice(settings.twilio_tts_voice)
        == "b2htR0pMe28pYwCY9gnP-flash_v2_5-1.05"
    )


@pytest.mark.asyncio
async def test_phone_agent_stream_uses_realtime_session() -> None:
    agent = PhoneLauraAgent(
        voice=MagicMock(),
        lead_service=MagicMock(),
        identity_service=MagicMock(),
        settings=Settings(
            OPENAI_API_KEY="sk-test",
            PERSISTENCE_PROVIDER="memory",
            DATABASE_ENABLED=False,
        ),
        lead_id=uuid4(),
        needs_identity=False,
        display_name="Ana",
    )

    async def fake_turn(_text: str, *, allow_tools: bool = True):
        _ = allow_tools
        yield "Hola Ana, "
        yield "soy Laura."

    mock_session = MagicMock()
    mock_session.connect = AsyncMock()
    mock_session.run_turn = fake_turn
    mock_session.cancel_response = AsyncMock()
    mock_session.close = AsyncMock()

    with patch.object(agent, "_build_session", return_value=mock_session):
        parts: list[str] = []
        async for chunk in agent.handle_user_prompt_stream("hola"):
            parts.append(chunk)

    assert "".join(parts) == "Hola Ana, soy Laura."
    mock_session.connect.assert_awaited()


@pytest.mark.asyncio
async def test_kickoff_response_create_disables_tools() -> None:
    settings = Settings(
        OPENAI_API_KEY="sk-test",
        OPENAI_REALTIME_MODEL="gpt-realtime-2.1",
        PERSISTENCE_PROVIDER="memory",
        DATABASE_ENABLED=False,
    )
    session = PhoneRealtimeSession(
        instructions="Eres Laura.",
        tools=[],
        tool_executor=AsyncMock(return_value={}),
        settings=settings,
    )

    class FakeWS:
        def __init__(self) -> None:
            self.sent: list[dict[str, Any]] = []

        async def send(self, raw: str) -> None:
            self.sent.append(json.loads(raw))

        async def close(self) -> None:
            return None

    fake = FakeWS()
    session._ws = fake  # noqa: SLF001
    session._closed = False
    session._recv_task = asyncio.create_task(asyncio.sleep(3600))  # noqa: SLF001

    async def enqueue_ok() -> None:
        await asyncio.sleep(0.01)
        await session._events.put(  # noqa: SLF001
            {"type": "response.output_text.delta", "delta": "Hola"}
        )
        await session._events.put(  # noqa: SLF001
            {"type": "response.done", "response": {"output": []}}
        )

    feeder = asyncio.create_task(enqueue_ok())
    parts: list[str] = []
    async for chunk in session.run_turn("kickoff", allow_tools=False):
        parts.append(chunk)
    await feeder
    creates = [p for p in fake.sent if p.get("type") == "response.create"]
    assert creates
    assert creates[0]["response"].get("tool_choice") == "none"
    assert "Hola" in "".join(parts)


@pytest.mark.asyncio
async def test_cancel_response_skipped_when_idle() -> None:
    settings = Settings(
        OPENAI_API_KEY="sk-test",
        OPENAI_REALTIME_MODEL="gpt-realtime-2.1",
        PERSISTENCE_PROVIDER="memory",
        DATABASE_ENABLED=False,
    )
    session = PhoneRealtimeSession(
        instructions="Eres Laura.",
        tools=[],
        tool_executor=AsyncMock(return_value={}),
        settings=settings,
    )

    class FakeWS:
        def __init__(self) -> None:
            self.sent: list[dict[str, Any]] = []

        async def send(self, raw: str) -> None:
            self.sent.append(json.loads(raw))

        async def close(self) -> None:
            return None

    fake = FakeWS()
    session._ws = fake  # noqa: SLF001
    session._closed = False
    session._response_active = False  # noqa: SLF001
    await session.cancel_response()
    assert fake.sent == []


@pytest.mark.asyncio
async def test_benign_cancel_error_does_not_apologize() -> None:
    settings = Settings(
        OPENAI_API_KEY="sk-test",
        OPENAI_REALTIME_MODEL="gpt-realtime-2.1",
        PERSISTENCE_PROVIDER="memory",
        DATABASE_ENABLED=False,
    )
    session = PhoneRealtimeSession(
        instructions="Eres Laura.",
        tools=[],
        tool_executor=AsyncMock(return_value={}),
        settings=settings,
    )

    class FakeWS:
        def __init__(self) -> None:
            self.sent: list[dict[str, Any]] = []

        async def send(self, raw: str) -> None:
            self.sent.append(json.loads(raw))

        async def close(self) -> None:
            return None

    fake = FakeWS()
    session._ws = fake  # noqa: SLF001
    session._closed = False
    session._recv_task = asyncio.create_task(asyncio.sleep(3600))  # noqa: SLF001

    async def enqueue_ok() -> None:
        await asyncio.sleep(0.01)
        await session._events.put(  # noqa: SLF001
            {
                "type": "error",
                "error": {
                    "code": "response_cancel_not_active",
                    "message": "Cancellation failed: no active response found",
                },
            }
        )
        await asyncio.sleep(0.01)
        await session._events.put(  # noqa: SLF001
            {"type": "response.output_text.delta", "delta": "Hola"}
        )
        await session._events.put(  # noqa: SLF001
            {"type": "response.done", "response": {"output": []}}
        )

    feeder = asyncio.create_task(enqueue_ok())
    parts: list[str] = []
    async for chunk in session.run_turn("hola"):
        parts.append(chunk)
    await feeder
    joined = "".join(parts)
    assert "problema" not in joined.lower()
    assert "Hola" in joined
