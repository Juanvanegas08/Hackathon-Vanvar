"""Twilio voice webhooks: Gather speech loop + optional ConversationRelay."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse
from twilio.twiml.voice_response import VoiceResponse

from app.api.deps import (
    get_identity_service,
    get_lead_service,
    get_phone_call_session_store,
    get_settings_dep,
    get_twilio_call_service,
    get_voice_orchestration_service,
)
from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.services.identity_service import IdentityService
from app.services.lead_service import LeadService
from app.services.phone_call_session_store import PhoneCallSessionStore
from app.services.phone_laura_agent import (
    PhoneLauraAgent,
    default_welcome_greeting,
    find_lead_by_phone,
)
from app.services.twilio_call_service import TwilioCallService
from app.services.voice_orchestration_service import VoiceOrchestrationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/twilio", tags=["twilio"])


def _form_dict(form: Any) -> dict[str, str]:
    return {str(k): str(v) for k, v in form.items()}


def _twilio_url(request: Request, settings: Settings) -> str:
    public = (settings.twilio_public_base_url or "").rstrip("/")
    path = request.url.path
    query = f"?{request.url.query}" if request.url.query else ""
    if public:
        return f"{public}{path}{query}"
    return str(request.url)


async def _read_validated_form(
    request: Request,
    settings: Settings,
    twilio: TwilioCallService,
) -> tuple[dict[str, str], bool]:
    form = _form_dict(await request.form())
    if not settings.twilio_validate_signature or not settings.twilio_auth_token:
        return form, True
    signature = request.headers.get("X-Twilio-Signature")
    ok = twilio.validate_request(
        url=_twilio_url(request, settings),
        params=form,
        signature=signature,
    )
    return form, ok


def _resolve_lead(
    leads: LeadService,
    lead_id_raw: str | None,
) -> tuple[UUID | None, Any]:
    if not lead_id_raw:
        return None, None
    try:
        lead_id = UUID(str(lead_id_raw))
        return lead_id, leads.get_lead(lead_id)
    except (ValueError, NotFoundError):
        return None, None


async def _cancel_generation(
    task: asyncio.Task[None] | None,
    agent: PhoneLauraAgent | None = None,
) -> None:
    # Solo cancelar OpenAI si aún hay generación en curso (evita response_cancel_not_active
    # que luego mataba el siguiente turno con "Disculpa, tuve un problema").
    running = task is not None and not task.done()
    if running and agent is not None:
        try:
            await agent.cancel()
        except Exception:  # noqa: BLE001
            logger.debug("agent.cancel failed", exc_info=True)
    if not running:
        return
    assert task is not None
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    except Exception:  # noqa: BLE001
        logger.exception("Error while cancelling ConversationRelay generation task")


async def _stream_prompt_to_twilio(
    websocket: WebSocket,
    agent: PhoneLauraAgent,
    prompt: str,
    *,
    kickoff: bool = False,
) -> None:
    """Stream Realtime text tokens to ConversationRelay (ElevenLabs TTS)."""
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    async def _produce() -> None:
        try:
            stream = (
                agent.kickoff()
                if kickoff
                else agent.handle_user_prompt_stream(prompt)
            )
            async for chunk in stream:
                await queue.put(chunk)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Phone agent stream failed")
            await queue.put(
                "Disculpa, tuve un problema tecnico. "
                "Me lo puedes repetir en un momento?"
            )
        finally:
            await queue.put(None)

    producer = asyncio.create_task(_produce())
    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            token = item if item is not None else ""
            # Do not strip: Twilio needs spaces between LLM tokens for TTS prosody.
            if token == "":
                continue
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "text",
                        "token": token,
                        "last": False,
                        "interruptible": True,
                    }
                )
            )

        await websocket.send_text(
            json.dumps(
                {
                    "type": "text",
                    "token": "",
                    "last": True,
                    "interruptible": True,
                }
            )
        )

        if agent.end_call_requested:
            reason = agent.end_call_reason or "other"
            logger.info("ConversationRelay end_call reason=%s", reason)
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "end",
                        "handoffData": json.dumps({"reason": reason}),
                    }
                )
            )
    except asyncio.CancelledError:
        logger.info("ConversationRelay generation cancelled (interrupt)")
        producer.cancel()
        try:
            await producer
        except asyncio.CancelledError:
            pass
        raise
    except Exception:
        logger.exception("ConversationRelay stream wrapper failed")
        producer.cancel()
        try:
            await producer
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
        try:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "text",
                        "token": (
                            "Disculpa, tuve un problema tecnico. "
                            "Me lo puedes repetir en un momento?"
                        ),
                        "last": True,
                        "interruptible": True,
                    }
                )
            )
        except Exception:  # noqa: BLE001
            pass
    else:
        if not producer.done():
            await producer


@router.post("/voice/inbound")
async def inbound_voice(
    request: Request,
    settings: Settings = Depends(get_settings_dep),
    twilio: TwilioCallService = Depends(get_twilio_call_service),
    leads: LeadService = Depends(get_lead_service),
    sessions: PhoneCallSessionStore = Depends(get_phone_call_session_store),
    voice: VoiceOrchestrationService = Depends(get_voice_orchestration_service),
    identity: IdentityService = Depends(get_identity_service),
) -> Response:
    form, ok = await _read_validated_form(request, settings, twilio)
    if not ok:
        return PlainTextResponse("Forbidden", status_code=403)

    caller = form.get("From") or ""
    lead = find_lead_by_phone(leads, caller) if caller else None
    needs_identity = lead is None
    greeting = default_welcome_greeting(
        display_name=lead.nombre if lead else None,
        needs_identity=needs_identity,
    )
    call_sid = form.get("CallSid") or ""
    if call_sid:
        sessions.get_or_create(
            call_sid=call_sid,
            voice=voice,
            lead_service=leads,
            identity_service=identity,
            settings=settings,
            lead_id=lead.id if lead else None,
            caller_phone=caller or None,
            needs_identity=needs_identity,
        )
    xml = twilio.build_voice_twiml(
        lead_id=lead.id if lead else None,
        welcome_greeting=greeting,
        needs_identity=needs_identity,
        caller_phone=caller or None,
    )
    return Response(content=xml, media_type="application/xml")


@router.post("/voice/outbound")
async def outbound_voice(
    request: Request,
    settings: Settings = Depends(get_settings_dep),
    twilio: TwilioCallService = Depends(get_twilio_call_service),
    leads: LeadService = Depends(get_lead_service),
    sessions: PhoneCallSessionStore = Depends(get_phone_call_session_store),
    voice: VoiceOrchestrationService = Depends(get_voice_orchestration_service),
    identity: IdentityService = Depends(get_identity_service),
) -> Response:
    form, ok = await _read_validated_form(request, settings, twilio)
    if not ok:
        return PlainTextResponse("Forbidden", status_code=403)

    lead_id, lead = _resolve_lead(
        leads,
        request.query_params.get("lead_id") or form.get("lead_id"),
    )
    greeting = default_welcome_greeting(
        display_name=lead.nombre if lead else None,
        needs_identity=lead is None,
    )
    caller_phone = form.get("To") or form.get("From")
    call_sid = form.get("CallSid") or ""
    if call_sid:
        sessions.get_or_create(
            call_sid=call_sid,
            voice=voice,
            lead_service=leads,
            identity_service=identity,
            settings=settings,
            lead_id=lead_id,
            caller_phone=caller_phone,
            needs_identity=lead is None,
        )
    xml = twilio.build_voice_twiml(
        lead_id=lead_id,
        welcome_greeting=greeting,
        needs_identity=lead is None,
        caller_phone=caller_phone,
    )
    logger.info(
        "Outbound TwiML mode=%s CallSid=%s lead_id=%s",
        settings.twilio_voice_mode,
        call_sid,
        lead_id,
    )
    return Response(content=xml, media_type="application/xml")


@router.post("/voice/turn")
async def voice_turn(
    request: Request,
    settings: Settings = Depends(get_settings_dep),
    twilio: TwilioCallService = Depends(get_twilio_call_service),
    leads: LeadService = Depends(get_lead_service),
    sessions: PhoneCallSessionStore = Depends(get_phone_call_session_store),
    voice: VoiceOrchestrationService = Depends(get_voice_orchestration_service),
    identity: IdentityService = Depends(get_identity_service),
) -> Response:
    """Handle one Gather speech turn and continue the conversation."""
    form, ok = await _read_validated_form(request, settings, twilio)
    if not ok:
        return PlainTextResponse("Forbidden", status_code=403)

    call_sid = form.get("CallSid") or "unknown"
    speech = (form.get("SpeechResult") or "").strip()
    lead_id, _lead = _resolve_lead(
        leads,
        request.query_params.get("lead_id") or form.get("lead_id"),
    )
    needs_identity = (
        str(request.query_params.get("needs_identity", "")).lower() == "true"
        or lead_id is None
    )
    caller_phone = form.get("From") or form.get("To")

    agent = sessions.get_or_create(
        call_sid=call_sid,
        voice=voice,
        lead_service=leads,
        identity_service=identity,
        settings=settings,
        lead_id=lead_id,
        caller_phone=caller_phone,
        needs_identity=needs_identity,
    )

    if not speech:
        reply = "No te escuche bien. Puedes repetirme, por favor?"
    else:
        logger.info("Gather speech CallSid=%s text=%s", call_sid, speech[:200])
        try:
            reply = await agent.handle_user_prompt(speech)
        except Exception:
            logger.exception("Phone gather turn failed")
            reply = "Disculpa, tuve un problema. Me lo repites en un momento?"

    # Keep replies short enough for phone TTS.
    if len(reply) > 900:
        reply = reply[:900].rsplit(" ", 1)[0] + "."

    xml = twilio.build_gather_twiml(
        lead_id=agent.lead_id or lead_id,
        say_text=reply,
        needs_identity=agent.needs_identity,
    )
    return Response(content=xml, media_type="application/xml")


@router.post("/voice/connect-status")
async def connect_status(
    request: Request,
    settings: Settings = Depends(get_settings_dep),
    twilio: TwilioCallService = Depends(get_twilio_call_service),
) -> Response:
    """Twilio posts here when <Connect><ConversationRelay> ends."""
    form, ok = await _read_validated_form(request, settings, twilio)
    if not ok:
        return PlainTextResponse("Forbidden", status_code=403)
    logger.info(
        "ConversationRelay Connect ended: CallSid=%s ErrorCode=%s ErrorMessage=%s "
        "HandoffData=%s SessionStatus=%s form=%s",
        form.get("CallSid"),
        form.get("ErrorCode"),
        form.get("ErrorMessage"),
        form.get("HandoffData"),
        form.get("SessionStatus"),
        {k: v for k, v in form.items() if k not in {"AccountSid", "ApiVersion"}},
    )
    response = VoiceResponse()
    response.hangup()
    return Response(content=str(response), media_type="application/xml")


@router.websocket("/conversation-relay")
async def conversation_relay_ws(
    websocket: WebSocket,
    settings: Settings = Depends(get_settings_dep),
    voice: VoiceOrchestrationService = Depends(get_voice_orchestration_service),
    leads: LeadService = Depends(get_lead_service),
    identity: IdentityService = Depends(get_identity_service),
) -> None:
    await websocket.accept()
    logger.info("ConversationRelay WebSocket accepted from %s", websocket.client)
    agent: PhoneLauraAgent | None = None
    generation_task: asyncio.Task[None] | None = None
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Non-JSON ConversationRelay message")
                continue

            event_type = event.get("type")
            if event_type == "setup":
                await _cancel_generation(generation_task, agent)
                generation_task = None
                if agent is not None:
                    await agent.close()
                params = event.get("customParameters") or {}
                lead_id = None
                display_name = None
                raw_lead = params.get("lead_id")
                if raw_lead:
                    try:
                        lead_id = UUID(str(raw_lead))
                        lead = leads.get_lead(lead_id)
                        display_name = (lead.nombre or "").strip() or None
                    except (ValueError, NotFoundError):
                        lead_id = None
                needs_identity = str(params.get("needs_identity", "")).lower() == "true"
                if lead_id is None:
                    needs_identity = True
                caller_phone = params.get("caller_phone") or event.get("from")
                agent = PhoneLauraAgent(
                    voice=voice,
                    lead_service=leads,
                    identity_service=identity,
                    settings=settings,
                    lead_id=lead_id,
                    caller_phone=caller_phone,
                    needs_identity=needs_identity,
                    display_name=display_name,
                )
                logger.info(
                    "ConversationRelay setup callSid=%s lead_id=%s needs_identity=%s",
                    event.get("callSid"),
                    lead_id,
                    needs_identity,
                )
                # Kickoff inmediato: connect ocurre dentro del stream (sin await serial).
                generation_task = asyncio.create_task(
                    _stream_prompt_to_twilio(
                        websocket, agent, "", kickoff=True
                    )
                )
                continue

            if event_type == "prompt":
                if not event.get("last", True):
                    continue
                if agent is None:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "text",
                                "token": "Un segundo, estoy preparando la llamada.",
                                "last": True,
                                "interruptible": True,
                            }
                        )
                    )
                    continue
                await _cancel_generation(generation_task, agent)
                prompt = event.get("voicePrompt") or ""
                generation_task = asyncio.create_task(
                    _stream_prompt_to_twilio(websocket, agent, prompt)
                )
                continue

            if event_type == "interrupt":
                logger.info(
                    "ConversationRelay interrupt callSid=%s utteranceUntilInterrupt=%s",
                    event.get("callSid"),
                    (event.get("utteranceUntilInterrupt") or "")[:80],
                )
                await _cancel_generation(generation_task, agent)
                generation_task = None
                continue

            if event_type == "error":
                logger.error(
                    "ConversationRelay error: %s",
                    event.get("description") or event,
                )
                continue

    except WebSocketDisconnect:
        logger.info("ConversationRelay WebSocket disconnected")
    except Exception:
        logger.exception("ConversationRelay WebSocket crashed")
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass
    finally:
        await _cancel_generation(generation_task, agent)
        if agent is not None:
            await agent.close()
