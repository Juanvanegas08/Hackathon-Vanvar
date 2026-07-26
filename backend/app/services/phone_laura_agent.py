"""Laura phone agent: OpenAI Realtime (text) + tools — same brain as web.

Transport: Twilio ConversationRelay STT → this agent → ElevenLabs TTS.
Keep behavior aligned with frontend/src/features/voice/createCasaListaRealtimeAgent.ts
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError, NotFoundError, ValidationBusinessError
from app.models.lead import ENGAGEMENT_LABEL_VALUES, CanalOrigen, Lead
from app.schemas.realtime import (
    VoiceAnswerRequest,
    VoiceCompleteRequest,
    VoiceEngagementRequest,
)
from app.services.identity_service import IdentityService
from app.services.laura_agent_instructions import (
    KICKOFF_USER_MESSAGE,
    build_laura_instructions,
)
from app.services.lead_service import LeadService
from app.services.phone_realtime_session import PhoneRealtimeSession
from app.services.voice_orchestration_service import VoiceOrchestrationService
from app.utils.phone import normalize_phone

logger = logging.getLogger(__name__)

QUESTION_HINTS = (
    "aclara",
    "aclarar",
    "explica",
    "explicar",
    "qué significa",
    "que significa",
    "no entend",
    "no te entend",
    "puedes repetir",
    "me puedes",
    "puedes decirme",
    "me puedes decir",
    "quiero saber",
    "quisiera saber",
    "por qué",
    "por que",
    "cómo es",
    "como es",
    "cómo funciona",
    "como funciona",
    "cómo hago",
    "como hago",
    "cuánto",
    "cuanto",
    "cuántos",
    "cuantos",
    "dónde",
    "donde",
    "cuándo",
    "cuando puedo",
    "cuál",
    "cual ",
    "cuáles",
    "cuales",
    "una duda",
    "tengo una duda",
    "una pregunta",
    "tengo una pregunta",
    "pregunta",
    "qué es",
    "que es",
    "qué son",
    "que son",
    "qué pasa",
    "que pasa",
    "no sé qué",
    "no se que",
    "qué quieres decir",
    "que quieres decir",
    "otra vez",
    "repite",
    "hay forma",
    "es posible",
    "se puede",
    "me recomiendas",
    "qué diferencia",
    "que diferencia",
    "y eso",
    "oye y",
    "pero y",
)

FILLERS = {
    "eh",
    "ehh",
    "mmm",
    "este",
    "este...",
    "hola",
    "ok",
    "okay",
    "ajá",
    "aja",
    "ya",
    "bueno",
    "no sé",
    "no se",
    "nada",
    "lo que sea",
    "dale",
    "sigue",
}


def _looks_like_user_question(transcript: str) -> bool:
    text = transcript.strip().lower()
    if not text:
        return False
    if "?" in text or "¿" in text:
        return True
    if any(hint in text for hint in QUESTION_HINTS):
        return True
    return bool(
        re.match(
            r"^(qué|que|cómo|como|cuánto|cuanto|dónde|donde|cuál|cual|por\s*qué|por\s*que)\b",
            text,
        )
    )


def _looks_like_non_answer(transcript: str) -> bool:
    text = transcript.strip().lower()
    if not text:
        return True
    if text in FILLERS:
        return True
    return bool(re.match(r"^(eh+|mm+|ah+|uhm+|este\.?)+$", text, flags=re.I))


def _tool_get_voice_context() -> dict[str, Any]:
    return {
        "type": "function",
        "name": "get_voice_context",
        "description": (
            "Obtiene el estado actual del perfil y la única pregunta que debe "
            "hacerse a continuación."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    }


def _tool_submit_answer() -> dict[str, Any]:
    return {
        "type": "function",
        "name": "submit_current_answer",
        "description": (
            "Guarda un dato del perfil SOLO cuando el usuario realmente RESPONDE "
            "la pregunta activa. Antes de llamar, clasifica el turno con userIntent. "
            "Si el usuario pregunta o tiene una duda: userIntent=\"question\", "
            "answersCurrentQuestion=false (o no llames la tool) y CONTÉSTALE en voz. "
            "Nunca trates una pregunta como si fuera el valor del campo."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "field": {"type": "string"},
                "rawTranscript": {"type": "string"},
                "normalizedValue": {
                    "type": ["string", "number", "boolean", "null"],
                },
                "action": {
                    "type": "string",
                    "enum": ["answer", "confirm", "correct", "skip"],
                },
                "answersCurrentQuestion": {"type": "boolean"},
                "userIntent": {
                    "type": "string",
                    "enum": ["answer", "question", "unclear", "off_topic", "filler"],
                },
            },
            "required": [
                "field",
                "rawTranscript",
                "normalizedValue",
                "action",
                "answersCurrentQuestion",
                "userIntent",
            ],
        },
    }


def _tool_report_engagement() -> dict[str, Any]:
    return {
        "type": "function",
        "name": "report_user_engagement",
        "description": (
            "Registra el sentimiento dominante del usuario para el asesor. "
            "Úsala casi nunca: solo 1 vez al cierre o si el tono cambia de forma "
            "extrema. NUNCA entre turnos normales (añade latencia)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "label": {
                    "type": "string",
                    "enum": list(ENGAGEMENT_LABEL_VALUES),
                },
                "score": {"type": ["number", "null"]},
                "reason": {"type": ["string", "null"]},
            },
            "required": ["label"],
        },
    }


def _tool_complete_profile() -> dict[str, Any]:
    return {
        "type": "function",
        "name": "complete_voice_profile",
        "description": (
            "Finaliza el perfilamiento cuando no queden preguntas y prepara "
            "resultados. OBLIGATORIO: incluye engagement_label/score/reason del "
            "sentimiento dominante (feliz/triste/enojado/consternado/grosero/"
            "cortes/interesado/…). Puede tardar. No llames tools extras antes; "
            "habla solo cuando tengas el resultado."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "engagement_label": {
                    "type": "string",
                    "enum": list(ENGAGEMENT_LABEL_VALUES),
                },
                "engagement_score": {"type": ["number", "null"]},
                "engagement_reason": {"type": ["string", "null"]},
            },
            "required": ["engagement_label"],
        },
    }


def _tool_resolve_identity() -> dict[str, Any]:
    return {
        "type": "function",
        "name": "resolve_identity",
        "description": (
            "Resuelve o crea el lead a partir del documento del usuario. "
            "Úsala solo cuando needs_identity=true y el usuario dio documento."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "documentType": {
                    "type": "string",
                    "enum": ["CC", "CE", "PP", "NIT"],
                },
                "documentNumber": {"type": "string"},
                "dataConsent": {"type": "boolean"},
            },
            "required": ["documentType", "documentNumber", "dataConsent"],
        },
    }


def _tool_end_call() -> dict[str, Any]:
    return {
        "type": "function",
        "name": "end_call",
        "description": (
            "Termina la llamada después de despedirte. Úsala si el usuario pide "
            "llamar más tarde, está ocupado, no quiere seguir, o se despide. "
            "OBLIGATORIO: registra engagement_label del sentimiento dominante "
            "(si no lo das, el backend lo infiere del reason)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "enum": ["callback_later", "busy", "goodbye", "other"],
                },
                "spoken_goodbye": {"type": "string"},
                "callback_note": {"type": "string"},
                "engagement_label": {
                    "type": "string",
                    "enum": list(ENGAGEMENT_LABEL_VALUES),
                },
                "engagement_score": {"type": ["number", "null"]},
                "engagement_reason": {"type": ["string", "null"]},
            },
            "required": ["reason"],
        },
    }


class PhoneLauraAgent:
    """Laura on phone via OpenAI Realtime text + ConversationRelay TTS."""

    def __init__(
        self,
        *,
        voice: VoiceOrchestrationService,
        lead_service: LeadService,
        identity_service: IdentityService,
        settings: Settings | None = None,
        lead_id: UUID | None = None,
        caller_phone: str | None = None,
        needs_identity: bool = False,
        display_name: str | None = None,
    ) -> None:
        self._voice = voice
        self._leads = lead_service
        self._identity = identity_service
        self._settings = settings or get_settings()
        self.lead_id = lead_id
        self.caller_phone = caller_phone
        self.needs_identity = needs_identity or lead_id is None
        self.display_name = (display_name or "").strip() or None
        self.end_call_requested = False
        self.end_call_reason: str | None = None
        self._kicked_off = False
        self._session: PhoneRealtimeSession | None = None

    @property
    def allow_thinking_filler(self) -> bool:
        return False

    def _active_tools(self) -> list[dict[str, Any]]:
        tools = [
            _tool_get_voice_context(),
            _tool_submit_answer(),
            _tool_report_engagement(),
            _tool_complete_profile(),
            _tool_end_call(),
        ]
        if self.needs_identity:
            tools.insert(0, _tool_resolve_identity())
        return tools

    def _initial_context_block(self) -> str:
        """Prefetch like web so kickoff can greet without a tool round-trip."""
        if self.lead_id is None:
            if self.needs_identity:
                return (
                    "Contexto inicial: needs_identity=true. "
                    "Saluda YA (2–3 frases: quién eres, 2–3 minutos, pide documento). "
                    "NO llames tools primero."
                )
            return (
                "Contexto inicial: saluda YA con marco de 2–3 minutos. "
                "NO llames tools primero."
            )
        try:
            ctx = self._voice.get_context(self.lead_id)
        except Exception:  # noqa: BLE001
            logger.exception("Prefetch voice context failed for phone kickoff")
            return (
                "Contexto inicial no disponible. Saluda YA con marco de 2–3 minutos "
                "y pregunta si siguen ahora. NO llames tools primero."
            )
        if ctx.display_name and not self.display_name:
            self.display_name = str(ctx.display_name).strip() or None
        next_q = ctx.next_question
        lines = [
            "Contexto inicial ya cargado (úsalo al saludar; NO llames get_voice_context primero):",
            f"display_name={ctx.display_name or ''}",
            f"progress={ctx.progress}",
            f"profile_completed={ctx.profile_completed}",
        ]
        if next_q is not None:
            lines.append(
                f"next_question.field={next_q.field}; intent={next_q.question}"
            )
        opening = (ctx.conversation_opening or "").strip()
        if opening:
            lines.append(f"opening_hint={opening}")
        lines.append(
            "Al kickoff: habla YA reformulando opening_hint (o saludo+marco 2–3 min). "
            "Cero tools en el primer turno."
        )
        return "\n".join(lines)

    def _build_session(self) -> PhoneRealtimeSession:
        if self.display_name is None and self.lead_id is not None:
            try:
                lead = self._leads.get_lead(self.lead_id)
                self.display_name = (lead.nombre or "").strip() or None
            except NotFoundError:
                pass
        instructions = build_laura_instructions(display_name=self.display_name)
        context_block = self._initial_context_block()
        if context_block:
            instructions = f"{instructions}\n{context_block}"
        if self.needs_identity:
            instructions += (
                "\nCanal teléfono: needs_identity=true. Antes de perfilar, "
                "pide documento con naturalidad y usa resolve_identity "
                "(después del saludo, no antes de hablar)."
            )
        return PhoneRealtimeSession(
            instructions=instructions,
            tools=self._active_tools(),
            tool_executor=self._execute_tool_async,
            settings=self._settings,
        )

    async def ensure_connected(self) -> None:
        if self._session is None:
            self._session = self._build_session()
        try:
            await self._session.connect()
        except Exception:
            # Drop broken session so the next turn can reconnect cleanly.
            await self.close()
            raise

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def cancel(self) -> None:
        if self._session is not None:
            await self._session.cancel_response()

    def warmup(self) -> None:
        """No-op: Realtime session connects on first turn / kickoff."""

    async def kickoff(self) -> AsyncIterator[str]:
        """Same kickoff spirit as web RealtimeSession.sendMessage(...)."""
        if self._kicked_off:
            return
        self._kicked_off = True
        async for chunk in self.handle_user_prompt_stream(
            KICKOFF_USER_MESSAGE,
            allow_tools=False,
        ):
            yield chunk

    async def handle_user_prompt(self, transcript: str) -> str:
        parts: list[str] = []
        async for chunk in self.handle_user_prompt_stream(transcript):
            parts.append(chunk)
        return "".join(parts).strip() or "Un segundo... me lo repites, por favor?"

    async def handle_user_prompt_stream(
        self,
        transcript: str,
        *,
        allow_tools: bool = True,
    ) -> AsyncIterator[str]:
        text = (transcript or "").strip()
        if not text:
            yield "No te escuche bien. Me lo repites, por favor?"
            return
        await self.ensure_connected()
        assert self._session is not None
        try:
            async for chunk in self._session.run_turn(text, allow_tools=allow_tools):
                if chunk:
                    yield chunk
        except asyncio.CancelledError:
            await self.cancel()
            raise
        except ConfigurationError:
            logger.exception("Phone Realtime configuration error")
            yield "Disculpa, tuve un problema tecnico. Me lo puedes repetir en un momento?"
        except Exception:
            logger.exception("Phone Realtime turn failed")
            yield "Disculpa, tuve un problema tecnico. Me lo puedes repetir en un momento?"

    async def _execute_tool_async(
        self,
        name: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        # Tools are sync against local services; keep async signature for the session.
        return self._execute_tool(name, args)

    def _execute_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        try:
            if name == "get_voice_context":
                return self._tool_get_voice_context()
            if name == "submit_current_answer":
                return self._tool_submit_answer(args)
            if name == "report_user_engagement":
                return self._tool_report_engagement(args)
            if name == "complete_voice_profile":
                return self._tool_complete(args)
            if name == "resolve_identity":
                return self._tool_resolve_identity(args)
            if name == "end_call":
                return self._tool_end_call(args)
            return {"ok": False, "error": f"Herramienta desconocida: {name}"}
        except (ValidationBusinessError, NotFoundError, ConfigurationError) as exc:
            return {"ok": False, "error": str(exc)}
        except Exception:
            logger.exception("Phone tool %s failed", name)
            return {"ok": False, "error": "Error interno al ejecutar la herramienta."}

    def _require_lead_id(self) -> UUID:
        if self.lead_id is None:
            raise ValidationBusinessError(
                "Primero debes identificar a la persona con resolve_identity."
            )
        return self.lead_id

    def _tool_get_voice_context(self) -> dict[str, Any]:
        lead_id = self._require_lead_id()
        ctx = self._voice.get_context(lead_id)
        next_q = None
        if ctx.next_question is not None:
            item = ctx.next_question
            next_q = {
                "field": item.field,
                "question": item.question,
                "type": (
                    item.type.value if hasattr(item.type, "value") else str(item.type)
                ),
                "confirmation_required": item.confirmation_required,
            }
        return {
            "known_lead": ctx.known_lead,
            "display_name": ctx.display_name,
            "identity_status": ctx.identity_status,
            "profile_completed": ctx.profile_completed,
            "progress": ctx.progress,
            "next_question": next_q,
            "conversation_opening": ctx.conversation_opening,
            "fields_to_confirm": ctx.fields_to_confirm,
            "warnings": ctx.warnings,
            "demo_mode": ctx.demo_mode,
        }

    def _reject_guidance(
        self,
        reason: str,
        kind: str = "invalid",
    ) -> dict[str, Any]:
        if kind == "question":
            guidance = (
                f"{reason} NO guardes nada. Contesta en 1–2 frases cortas y retoma "
                "la pregunta activa. Sin muletillas."
            )
        elif kind == "non_answer":
            guidance = (
                f"{reason} NO guardes nada. Repregunta el dato en una sola frase corta."
            )
        else:
            guidance = (
                f"{reason} NO guardes nada. Aclara en una frase y repregunta el "
                "campo activo."
            )
        return {
            "accepted": False,
            "clarification_required": True,
            "user_turn_kind": kind,
            "assistant_guidance": guidance,
            "validation_message": reason,
        }

    def _tool_submit_answer(self, args: dict[str, Any]) -> dict[str, Any]:
        lead_id = self._require_lead_id()
        raw = str(args.get("rawTranscript") or "")
        user_intent = str(args.get("userIntent") or "unclear")
        answers = bool(args.get("answersCurrentQuestion"))
        action = str(args.get("action") or "answer")
        normalized = args.get("normalizedValue")

        if user_intent == "question" or _looks_like_user_question(raw):
            return self._reject_guidance(
                "El usuario está preguntando o pidiendo aclaración, no respondiendo el campo.",
                "question",
            )
        if not answers or user_intent in {"unclear", "off_topic", "filler"}:
            kind = "non_answer" if user_intent in {"filler", "off_topic"} else "invalid"
            return self._reject_guidance(
                "El turno no es una respuesta usable a la pregunta activa.",
                kind,
            )
        if _looks_like_non_answer(raw):
            return self._reject_guidance(
                "El audio/transcript no contiene una respuesta usable al campo.",
                "non_answer",
            )
        if action == "answer" and (
            normalized is None
            or (isinstance(normalized, str) and not normalized.strip())
        ):
            return self._reject_guidance(
                "No hay normalizedValue usable para la pregunta activa.",
                "invalid",
            )

        result = self._voice.submit_answer(
            lead_id,
            VoiceAnswerRequest(
                field=str(args.get("field") or ""),
                raw_transcript=raw,
                normalized_value=normalized,
                action=action,  # type: ignore[arg-type]
            ),
        )
        payload = result.model_dump(mode="json")
        if not result.accepted or result.clarification_required:
            looks_q = _looks_like_user_question(raw)
            payload["user_turn_kind"] = "question" if looks_q else "invalid"
            if looks_q:
                payload["assistant_guidance"] = (
                    f"{result.assistant_guidance} El usuario parece preguntar: "
                    "respóndele primero y luego retoma el perfil."
                )
            else:
                payload["assistant_guidance"] = (
                    f"{result.assistant_guidance or 'La respuesta no fue aceptada.'} "
                    "Vuelve a preguntar la misma pregunta hasta obtener una respuesta "
                    "válida. No avances al siguiente campo."
                )
        else:
            payload["speak_now"] = (
                "Di SOLO la siguiente pregunta, corta y sencilla (ideal ≤12 palabras). "
                "Varía la formulación. Prohibido: muletillas, eco, "
                '"reporto/guardo/envío el dato", o menús tipo continuar/editar.'
            )
        return payload

    def _tool_report_engagement(self, args: dict[str, Any]) -> dict[str, Any]:
        lead_id = self._require_lead_id()
        label = str(args.get("label") or "desconocido")
        score = args.get("score")
        reason = args.get("reason")
        score_int = int(score) if isinstance(score, (int, float)) else None
        result = self._voice.report_engagement(
            lead_id,
            VoiceEngagementRequest(
                label=label,  # type: ignore[arg-type]
                score=score_int,
                reason=str(reason) if reason is not None else None,
            ),
        )
        return result.model_dump(mode="json")

    def _tool_complete(self, args: dict[str, Any] | None = None) -> dict[str, Any]:
        lead_id = self._require_lead_id()
        args = args or {}
        score = args.get("engagement_score")
        score_int = int(score) if isinstance(score, (int, float)) else None
        complete_payload = VoiceCompleteRequest(
            engagement_label=args.get("engagement_label"),  # type: ignore[arg-type]
            engagement_score=score_int,
            engagement_reason=(
                str(args["engagement_reason"])
                if args.get("engagement_reason") is not None
                else None
            ),
        )
        try:
            result = self._voice.complete(lead_id, complete_payload)
            payload = result.model_dump(mode="json")
            if payload.get("completed"):
                payload["speak_now"] = (
                    "LEE EN VOZ ALTA SOLO el assistant_closing o spoken_summary. "
                    "No inventes menús (continuar/editar/cancelar). "
                    "No agregues preguntas nuevas."
                )
            return {
                "completed": payload.get("completed"),
                "assistant_closing": payload.get("assistant_closing"),
                "spoken_summary": payload.get("spoken_summary"),
                "navigation_path": payload.get("navigation_path"),
                "recommendations_count": payload.get("recommendations_count"),
                "top_project": payload.get("top_project"),
                "recommended_projects": payload.get("recommended_projects"),
                "disclaimer": payload.get("disclaimer"),
                "engagement_label": payload.get("engagement_label"),
                "engagement_score": payload.get("engagement_score"),
                "engagement_reason": payload.get("engagement_reason"),
                "speak_now": payload.get("speak_now"),
            }
        except Exception as exc:  # noqa: BLE001
            logger.exception("complete_voice_profile failed")
            return {
                "completed": False,
                "error": True,
                "retryable": True,
                "message": str(exc) or "No se pudo completar el cierre ahora.",
                "assistant_guidance": (
                    "Di brevemente que estás preparando la recomendación y vuelve "
                    "a llamar complete_voice_profile una sola vez. No digas que el "
                    "servicio está caído ni sin conexión."
                ),
            }

    def _tool_resolve_identity(self, args: dict[str, Any]) -> dict[str, Any]:
        document_type = str(args.get("documentType") or "CC").upper()
        document_number = str(args.get("documentNumber") or "").strip()
        data_consent = bool(args.get("dataConsent", True))
        if not document_number:
            return {"ok": False, "error": "Falta el número de documento."}

        lead, context = self._identity.create_lead_from_identity(
            document_type=document_type,
            document_number=document_number,
            data_consent=data_consent,
        )
        if self.caller_phone:
            try:
                phone = normalize_phone(self.caller_phone)
                lead = self._leads.apply_lead_updates(
                    lead.id,
                    {
                        "telefono": phone,
                        "canal_origen": CanalOrigen.OTRO,
                    },
                )
            except (ValueError, ValidationBusinessError):
                pass

        self.lead_id = lead.id
        self.needs_identity = False
        self.display_name = (lead.nombre or "").strip() or self.display_name
        # Refresh tools without identity on next reconnect is complex; session
        # already has resolve_identity — harmless if unused.
        return {
            "ok": True,
            "lead_id": str(lead.id),
            "display_name": lead.nombre,
            "context": context,
            "assistant_guidance": (
                "Identidad resuelta. Llama get_voice_context y continúa con "
                "una pregunta a la vez."
            ),
        }

    def _tool_end_call(self, args: dict[str, Any]) -> dict[str, Any]:
        reason = str(args.get("reason") or "other").strip() or "other"
        goodbye = (args.get("spoken_goodbye") or "").strip()
        callback_note = (args.get("callback_note") or "").strip()
        if not goodbye:
            if reason == "callback_later":
                if callback_note:
                    goodbye = (
                        f"Listo, perfecto. Te contacto {callback_note}. "
                        "Que estés bien."
                    )
                else:
                    goodbye = "Listo, perfecto. Te contacto más tarde. Que estés bien."
            elif reason == "busy":
                goodbye = "Listo, no te preocupes. Hablamos después."
            else:
                goodbye = "Listo, perfecto. Chao, que estés bien."

        engagement_label = args.get("engagement_label")
        engagement_score = args.get("engagement_score")
        engagement_reason = args.get("engagement_reason")
        score_int = (
            int(engagement_score)
            if isinstance(engagement_score, (int, float))
            else None
        )
        fallback_label, fallback_score, fallback_reason = _end_call_engagement_fallback(
            reason
        )
        if self.lead_id is not None:
            try:
                self._voice.ensure_engagement(
                    self.lead_id,
                    label=str(engagement_label) if engagement_label else None,
                    score=score_int,
                    reason=(
                        str(engagement_reason)
                        if engagement_reason is not None
                        else None
                    ),
                    fallback_label=fallback_label,
                    fallback_score=fallback_score,
                    fallback_reason=fallback_reason,
                    overwrite=True,
                )
            except Exception:  # noqa: BLE001
                logger.exception("Failed to persist engagement on end_call")

        self.end_call_requested = True
        self.end_call_reason = reason
        return {
            "end_call": True,
            "reason": reason,
            "spoken_goodbye": goodbye,
            "callback_note": callback_note or None,
            "engagement_label": engagement_label or fallback_label,
            "ok": True,
        }


def _end_call_engagement_fallback(reason: str) -> tuple[str, int, str]:
    if reason == "busy":
        return (
            "ocupado",
            40,
            "Usuario ocupado; se cortó la llamada a petición suya.",
        )
    if reason == "callback_later":
        return (
            "ocupado",
            45,
            "Usuario pidió callback más tarde.",
        )
    if reason == "goodbye":
        return (
            "interesado",
            65,
            "Cierre normal de la llamada al despedirse.",
        )
    return (
        "desconocido",
        50,
        "Llamada terminada sin predisposición explícita.",
    )


def find_lead_by_phone(lead_service: LeadService, phone: str) -> Lead | None:
    """Find an existing lead whose telefono matches the given phone."""
    try:
        target = normalize_phone(phone)
    except ValueError:
        return None
    for lead in lead_service.list_leads():
        if lead.telefono and normalize_phone(lead.telefono) == target:
            return lead
    return None


def default_welcome_greeting(*, display_name: str | None, needs_identity: bool) -> str:
    """Short Twilio pre-roll so the caller hears audio in <1s while Realtime starts."""
    name = (display_name or "").strip()
    hello = f"Hola {name}" if name else "Hola"
    if needs_identity:
        return (
            f"{hello}, soy Laura de Colsubsidio. "
            "Un segundo y te oriento con vivienda."
        )
    return (
        f"{hello}, soy Laura de Colsubsidio. "
        "Dame un segundo y arrancamos."
    )

def web_tool_names() -> list[str]:
    """Tool names shared with the web Realtime agent (plus phone extras separately)."""
    return [
        "get_voice_context",
        "submit_current_answer",
        "report_user_engagement",
        "complete_voice_profile",
    ]
