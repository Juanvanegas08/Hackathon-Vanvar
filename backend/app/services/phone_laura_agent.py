"""Laura phone agent: OpenAI chat + tools backed by VoiceOrchestrationService.

Keep AGENT_INSTRUCTIONS aligned with
frontend/src/features/voice/createCasaListaRealtimeAgent.ts
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from uuid import UUID

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError, NotFoundError, ValidationBusinessError
from app.models.lead import CanalOrigen, Lead
from app.schemas.realtime import VoiceAnswerRequest, VoiceEngagementRequest
from app.services.identity_service import IdentityService
from app.services.lead_service import LeadService
from app.services.voice_orchestration_service import VoiceOrchestrationService
from app.utils.phone import normalize_phone

logger = logging.getLogger(__name__)

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"

# Keep aligned with frontend/src/features/voice/createCasaListaRealtimeAgent.ts
AGENT_INSTRUCTIONS = """
Eres Laura, asesora virtual de Colsubsidio para orientación de vivienda (plataforma CasaLista).
Eres mujer, hablas con voz femenina y te presentas siempre como Laura.

Identidad y propósito:
- Eres una agente de Colsubsidio que ayuda a las personas a tomar la mejor decisión para escoger vivienda.
- Tu rol es acompañar con calidez, escuchar el perfil y orientar opciones compatibles de forma clara y honesta.
- No eres un call center genérico ni un formulario: eres Laura, asesora de Colsubsidio.

IDIOMA (obligatorio):
- Habla SOLO en español colombiano. Nunca cambies a inglés u otro idioma.
- Si el audio se oye raro o parece otro idioma, asume que la persona habló en español mal transcrito: pide que repita en español, no respondas en otro idioma.

Hablas de forma natural, cercana y calmada — como una asesora real en una llamada amable.
Evita tono corporativo, frases de manual y ritmo de checklist.

Tu propósito operativo es conversar para completar el perfil de vivienda (afiliación, hogar, capacidad orientativa y preferencias) y entregar opciones compatibles.
Las preguntas de voz deben seguir la misma intención del flujo escrito: usa la pregunta o intención que indique el backend, una por una, y espera la respuesta antes de continuar.
Puedes reformularla con palabras orales propias, sin cambiar el significado.

Clasificación de cada turno del usuario (CRÍTICO — hazlo SIEMPRE antes de hablar o guardar):
Escucha lo que DIJO de verdad. No asumas que está contestando tu pregunta solo porque tú preguntaste algo.

Clasifica mentalmente el turno en UNA de estas:
A) RESPUESTA — contesta de forma usable la pregunta activa (sí/no, número, lugar, plazo, etc.).
B) PREGUNTA O DUDA — te pide explicación, opinión, ejemplo, o pregunta otra cosa (aunque no diga "¿").
C) FUERA DE TEMA / RUIDO — no responde ni pregunta con sentido (filler, audio vacío, "mmm").
D) AMBIGUA — podría ser respuesta o no; pide confirmación breve.

Cómo actuar según la clase:
A) RESPUESTA clara → submit_current_answer con answersCurrentQuestion=true y userIntent="answer".
B) PREGUNTA O DUDA → NO guardes nada. NO digas solo "ok" y repitas tu pregunta.
   1) Contesta de verdad lo que preguntó (2–5 frases, en español, con criterio útil).
   2) Si no sabes un dato exacto (tasas, cupos, precios oficiales), dilo y orienta en general.
   3) Solo DESPUÉS, invita a retomar: "cuando quieras seguimos con…" + la pregunta pendiente.
C) FUERA DE TEMA / RUIDO → no guardes; aclara qué necesitas y reformula la pregunta activa.
D) AMBIGUA → "¿me estás diciendo que…?" o "¿eso era una pregunta o me estás respondiendo X?". No guardes hasta confirmar.

Estilo conversacional:
- Al empezar: preséntate como Laura, agente de Colsubsidio, di en una frase que estás para ayudar a elegir la mejor opción de vivienda, y luego pasa a la primera pregunta.
- Reconoce lo que dijo con variedad. Casi nunca digas "gracias".
- En el flujo normal: respuestas cortas (una o dos frases). Cuando aclaras una duda: hasta 3–4 frases.
- Si interrumpe, detente y escucha.

Lectura de tono e interés (persistir):
- Clasifica la predisposición en: interesado, indeciso, molesto, trolleando, ocupado o desconocido.
- Cuando detectes un cambio claro de tono, llama report_user_engagement.

Reglas obligatorias:
1. Haz únicamente una pregunta principal a la vez y espera la respuesta del usuario.
2. No inventes datos de proyectos, cupos, tasas ni aprobaciones.
3. El backend de CasaLista es la única fuente de verdad para guardar datos y recomendaciones.
4. Antes de comenzar el perfil, si needs_identity es true o no hay lead, usa resolve_identity con el documento.
5. Si ya hay lead, consulta get_voice_context antes de perfilar.
6. Usa submit_current_answer SOLO si el turno es RESPUESTA (userIntent="answer" y answersCurrentQuestion=true).
7. Para situacion_crediticia usa: sin_reportes, al_dia, atrasos_menores, atrasos_mayores, en_proceso_normalizacion, desconocida.
   Para plazo_compra: inmediato, 3_meses, 6_meses, 12_meses, mas_de_un_ano, no_definido.
8. No afirmes que guardaste información hasta que la herramienta confirme éxito (accepted=true).
9. No preguntes información que ya esté confirmada.
10. No prometas aprobación de crédito ni vivienda garantizada.
11. No menciones IDs, endpoints, JSON, herramientas ni detalles técnicos.
12. Cuando el backend indique que el perfil está completo, llama a complete_voice_profile.
13. Utiliza la frase de cierre entregada por la herramienta, dicha de forma natural.
14. Después del cierre, no hagas más preguntas de perfilamiento.
15. Preséntate como Laura (Colsubsidio). CasaLista es la plataforma de apoyo.
"""

QUESTION_HINTS = (
    "aclara",
    "explica",
    "qué significa",
    "que significa",
    "no entend",
    "me puedes",
    "puedes decirme",
    "quiero saber",
    "por qué",
    "por que",
    "cómo",
    "como ",
    "cuánto",
    "cuanto",
    "dónde",
    "donde",
    "cuál",
    "cual ",
    "una duda",
    "pregunta",
    "qué es",
    "que es",
)

FILLERS = {
    "eh",
    "ehh",
    "mmm",
    "este",
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


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "resolve_identity",
            "description": (
                "Resuelve o crea el lead a partir del documento del usuario. "
                "Úsala al inicio de llamadas entrantes cuando aún no hay perfil."
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
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_voice_context",
            "description": "Obtiene el estado actual del perfil y la siguiente pregunta.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_current_answer",
            "description": (
                "Guarda un dato del perfil SOLO cuando el usuario responde la pregunta activa."
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
        },
    },
    {
        "type": "function",
        "function": {
            "name": "report_user_engagement",
            "description": "Registra predisposición/sentimiento del usuario.",
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {
                        "type": "string",
                        "enum": [
                            "interesado",
                            "indeciso",
                            "molesto",
                            "trolleando",
                            "ocupado",
                            "desconocido",
                        ],
                    },
                    "score": {"type": ["integer", "null"]},
                    "reason": {"type": ["string", "null"]},
                },
                "required": ["label", "score", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_voice_profile",
            "description": "Cierra el perfil y genera recomendaciones cuando el backend indique que está completo.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


class PhoneLauraAgent:
    """Stateful Laura agent for one Twilio ConversationRelay session."""

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
    ) -> None:
        self._voice = voice
        self._leads = lead_service
        self._identity = identity_service
        self._settings = settings or get_settings()
        self.lead_id = lead_id
        self.caller_phone = caller_phone
        self.needs_identity = needs_identity or lead_id is None
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": AGENT_INSTRUCTIONS},
            {
                "role": "system",
                "content": (
                    f"Canal: llamada telefónica. needs_identity={self.needs_identity}. "
                    f"lead_id={self.lead_id}. caller_phone={self.caller_phone}."
                ),
            },
        ]

    def _require_api_key(self) -> str:
        key = self._settings.openai_api_key
        if not key:
            raise ConfigurationError("OPENAI_API_KEY no configurada")
        return key

    def _require_lead_id(self) -> UUID:
        if self.lead_id is None:
            raise ValidationBusinessError(
                "Primero debes identificar a la persona con resolve_identity."
            )
        return self.lead_id

    async def handle_user_prompt(self, transcript: str) -> str:
        """Process one ConversationRelay prompt and return spoken text."""
        text = (transcript or "").strip()
        if not text:
            return "No te escuché bien. ¿Me lo repites, por favor?"

        self.messages.append({"role": "user", "content": text})
        reply = await self._run_tool_loop()
        self.messages.append({"role": "assistant", "content": reply})
        # Keep history bounded for long calls.
        if len(self.messages) > 40:
            self.messages = [self.messages[0], self.messages[1], *self.messages[-36:]]
        return reply

    async def _run_tool_loop(self, *, max_rounds: int = 8) -> str:
        key = self._require_api_key()
        model = self._settings.openai_phone_model
        timeout = self._settings.openai_request_timeout_seconds

        for _ in range(max_rounds):
            payload = {
                "model": model,
                "messages": self.messages,
                "tools": TOOL_DEFINITIONS,
                "tool_choice": "auto",
                "temperature": 0.4,
            }
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    OPENAI_CHAT_URL,
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            if response.status_code >= 400:
                logger.error("OpenAI phone agent error: %s", response.text[:500])
                raise ConfigurationError("No pude procesar el turno de la llamada.")

            data = response.json()
            message = data["choices"][0]["message"]
            tool_calls = message.get("tool_calls") or []
            self.messages.append(message)

            if not tool_calls:
                content = (message.get("content") or "").strip()
                return content or "Un segundo… ¿me repites, por favor?"

            for call in tool_calls:
                name = call["function"]["name"]
                raw_args = call["function"].get("arguments") or "{}"
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    args = {}
                result = self._execute_tool(name, args)
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    }
                )

        return "Un segundo, estoy organizando tu información. ¿Seguimos?"

    def _execute_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        try:
            if name == "resolve_identity":
                return self._tool_resolve_identity(args)
            if name == "get_voice_context":
                return self._tool_get_context()
            if name == "submit_current_answer":
                return self._tool_submit_answer(args)
            if name == "report_user_engagement":
                return self._tool_engagement(args)
            if name == "complete_voice_profile":
                return self._tool_complete()
            return {"ok": False, "error": f"Herramienta desconocida: {name}"}
        except (ValidationBusinessError, NotFoundError, ConfigurationError) as exc:
            return {"ok": False, "error": str(exc)}
        except Exception:
            logger.exception("Phone tool %s failed", name)
            return {"ok": False, "error": "Error interno al ejecutar la herramienta."}

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
        return {
            "ok": True,
            "lead_id": str(lead.id),
            "display_name": lead.nombre,
            "context": context,
            "assistant_guidance": (
                "Identidad resuelta. Ahora llama get_voice_context y continúa el perfil."
            ),
        }

    def _tool_get_context(self) -> dict[str, Any]:
        lead_id = self._require_lead_id()
        ctx = self._voice.get_context(lead_id)
        return {
            "known_lead": ctx.known_lead,
            "display_name": ctx.display_name,
            "identity_status": ctx.identity_status,
            "profile_completed": ctx.profile_completed,
            "progress": ctx.progress,
            "next_question": (
                {
                    "field": ctx.next_question.field,
                    "question": ctx.next_question.question,
                    "type": (
                        ctx.next_question.type.value
                        if hasattr(ctx.next_question.type, "value")
                        else str(ctx.next_question.type)
                    ),
                    "confirmation_required": ctx.next_question.confirmation_required,
                }
                if ctx.next_question
                else None
            ),
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
                f"{reason} NO guardes nada. PRIMERO responde con sustancia a la duda "
                "y luego retoma la pregunta activa."
            )
        elif kind == "non_answer":
            guidance = (
                f"{reason} NO guardes nada. Aclara qué dato necesitas y repregunta."
            )
        else:
            guidance = f"{reason} NO guardes nada. Explica y repregunta el campo activo."
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
        return payload

    def _tool_engagement(self, args: dict[str, Any]) -> dict[str, Any]:
        lead_id = self._require_lead_id()
        result = self._voice.report_engagement(
            lead_id,
            VoiceEngagementRequest(
                label=args.get("label") or "desconocido",  # type: ignore[arg-type]
                score=args.get("score"),
                reason=args.get("reason"),
            ),
        )
        return result.model_dump(mode="json")

    def _tool_complete(self) -> dict[str, Any]:
        lead_id = self._require_lead_id()
        result = self._voice.complete(lead_id)
        return result.model_dump(mode="json")


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
    if needs_identity:
        return (
            "Hola, soy Laura, asesora de Colsubsidio. "
            "Para orientarte con vivienda, ¿me confirmas tu tipo de documento "
            "y número, por ejemplo cédula y los dígitos?"
        )
    name = (display_name or "").strip()
    if name:
        return (
            f"Hola {name}, soy Laura, asesora de Colsubsidio. "
            "Te llamo para ayudarte a elegir la mejor opción de vivienda. "
            "¿Seguimos?"
        )
    return (
        "Hola, soy Laura, asesora de Colsubsidio. "
        "Te llamo para ayudarte a elegir la mejor opción de vivienda. "
        "¿Seguimos?"
    )
