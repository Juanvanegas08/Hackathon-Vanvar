"""Twilio voice webhooks and ConversationRelay WebSocket."""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse

from app.api.deps import (
    get_identity_service,
    get_lead_service,
    get_settings_dep,
    get_twilio_call_service,
    get_voice_orchestration_service,
)
from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.services.identity_service import IdentityService
from app.services.lead_service import LeadService
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


@router.post("/voice/inbound")
async def inbound_voice(
    request: Request,
    settings: Settings = Depends(get_settings_dep),
    twilio: TwilioCallService = Depends(get_twilio_call_service),
    leads: LeadService = Depends(get_lead_service),
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
    xml = twilio.build_conversation_relay_twiml(
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
) -> Response:
    form, ok = await _read_validated_form(request, settings, twilio)
    if not ok:
        return PlainTextResponse("Forbidden", status_code=403)

    lead_id_raw = request.query_params.get("lead_id") or form.get("lead_id")
    lead = None
    lead_id: UUID | None = None
    if lead_id_raw:
        try:
            lead_id = UUID(str(lead_id_raw))
            lead = leads.get_lead(lead_id)
        except (ValueError, NotFoundError):
            lead = None
            lead_id = None

    greeting = default_welcome_greeting(
        display_name=lead.nombre if lead else None,
        needs_identity=lead is None,
    )
    xml = twilio.build_conversation_relay_twiml(
        lead_id=lead_id,
        welcome_greeting=greeting,
        needs_identity=lead is None,
        caller_phone=form.get("To") or form.get("From"),
    )
    return Response(content=xml, media_type="application/xml")


@router.websocket("/conversation-relay")
async def conversation_relay_ws(
    websocket: WebSocket,
    settings: Settings = Depends(get_settings_dep),
    voice: VoiceOrchestrationService = Depends(get_voice_orchestration_service),
    leads: LeadService = Depends(get_lead_service),
    identity: IdentityService = Depends(get_identity_service),
) -> None:
    await websocket.accept()
    agent: PhoneLauraAgent | None = None
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
                params = event.get("customParameters") or {}
                lead_id = None
                raw_lead = params.get("lead_id")
                if raw_lead:
                    try:
                        lead_id = UUID(str(raw_lead))
                        leads.get_lead(lead_id)
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
                )
                logger.info(
                    "ConversationRelay setup callSid=%s lead_id=%s needs_identity=%s",
                    event.get("callSid"),
                    lead_id,
                    needs_identity,
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
                            }
                        )
                    )
                    continue
                prompt = event.get("voicePrompt") or ""
                try:
                    reply = await agent.handle_user_prompt(prompt)
                except Exception:
                    logger.exception("Phone agent failed")
                    reply = (
                        "Disculpa, tuve un problema técnico. "
                        "¿Me lo puedes repetir en un momento?"
                    )
                await websocket.send_text(
                    json.dumps({"type": "text", "token": reply, "last": True})
                )
                continue

            if event_type == "interrupt":
                continue

            if event_type == "error":
                logger.error("ConversationRelay error: %s", event.get("description"))
                continue

    except WebSocketDisconnect:
        logger.info("ConversationRelay WebSocket disconnected")
    except Exception:
        logger.exception("ConversationRelay WebSocket crashed")
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass
