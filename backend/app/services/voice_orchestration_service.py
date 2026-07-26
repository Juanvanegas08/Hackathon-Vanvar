"""Voice orchestration services that wrap existing profiling logic."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from app.core.exceptions import ValidationBusinessError
from app.models.lead import (
    CreditSituation,
    DataSource,
    EngagementLabel,
    FieldProvenance,
    Lead,
    PurchaseTimeline,
    QuestionFieldType,
)
from app.schemas.evaluation import NextQuestion
from app.schemas.realtime import (
    VoiceAnswerRequest,
    VoiceAnswerResponse,
    VoiceCompleteRequest,
    VoiceCompleteResponse,
    VoiceContextResponse,
    VoiceEngagementRequest,
    VoiceEngagementResponse,
)
from app.services.identity_service import IdentityService
from app.services.lead_service import LeadService
from app.services.question_service import QuestionService
from app.services.recommendation_service import RecommendationService
from app.utils.profile_progress import compute_profile_progress

CURRENCY_FIELDS = {
    "salario_mensual",
    "ingreso_hogar",
    "ahorro",
    "obligaciones_mensuales",
}
INTEGER_FIELDS = {
    "personas_hogar",
    "personas_a_cargo",
    "beneficiarios_registrados",
}
BOOLEAN_FIELDS = {
    "afiliado",
    "tiene_vivienda",
    "consentimiento",
    "data_consent",
}

# Natural-language aliases → canonical enum values for voice answers.
CREDIT_SITUATION_ALIASES: dict[str, CreditSituation] = {
    "sin_reportes": CreditSituation.SIN_REPORTES,
    "sin reportes": CreditSituation.SIN_REPORTES,
    "sin reporte": CreditSituation.SIN_REPORTES,
    "limpio": CreditSituation.SIN_REPORTES,
    "al_dia": CreditSituation.AL_DIA,
    "al dia": CreditSituation.AL_DIA,
    "al día": CreditSituation.AL_DIA,
    "atrasos_menores": CreditSituation.ATRASOS_MENORES,
    "atrasos menores": CreditSituation.ATRASOS_MENORES,
    "atrasos_mayores": CreditSituation.ATRASOS_MAYORES,
    "atrasos mayores": CreditSituation.ATRASOS_MAYORES,
    "en_proceso_normalizacion": CreditSituation.EN_PROCESO_NORMALIZACION,
    "en normalizacion": CreditSituation.EN_PROCESO_NORMALIZACION,
    "en normalización": CreditSituation.EN_PROCESO_NORMALIZACION,
    "desconocida": CreditSituation.DESCONOCIDA,
    "no se": CreditSituation.DESCONOCIDA,
    "no sé": CreditSituation.DESCONOCIDA,
    "no estoy seguro": CreditSituation.DESCONOCIDA,
    "no estoy segura": CreditSituation.DESCONOCIDA,
}

PURCHASE_TIMELINE_ALIASES: dict[str, PurchaseTimeline] = {
    "inmediato": PurchaseTimeline.INMEDIATO,
    "de inmediato": PurchaseTimeline.INMEDIATO,
    "ya": PurchaseTimeline.INMEDIATO,
    "3_meses": PurchaseTimeline.TRES_MESES,
    "3 meses": PurchaseTimeline.TRES_MESES,
    "tres meses": PurchaseTimeline.TRES_MESES,
    "6_meses": PurchaseTimeline.SEIS_MESES,
    "6 meses": PurchaseTimeline.SEIS_MESES,
    "seis meses": PurchaseTimeline.SEIS_MESES,
    "12_meses": PurchaseTimeline.DOCE_MESES,
    "12 meses": PurchaseTimeline.DOCE_MESES,
    "doce meses": PurchaseTimeline.DOCE_MESES,
    "un ano": PurchaseTimeline.DOCE_MESES,
    "un año": PurchaseTimeline.DOCE_MESES,
    "mas_de_un_ano": PurchaseTimeline.MAS_DE_UN_ANO,
    "mas de un ano": PurchaseTimeline.MAS_DE_UN_ANO,
    "más de un año": PurchaseTimeline.MAS_DE_UN_ANO,
    "no_definido": PurchaseTimeline.NO_DEFINIDO,
    "no definido": PurchaseTimeline.NO_DEFINIDO,
    "aun no": PurchaseTimeline.NO_DEFINIDO,
    "aún no": PurchaseTimeline.NO_DEFINIDO,
}


class VoiceOrchestrationService:
    """Safe voice-facing facade over lead, identity and recommendation services."""

    def __init__(
        self,
        lead_service: LeadService,
        identity_service: IdentityService,
        question_service: QuestionService | None = None,
        recommendation_service: RecommendationService | None = None,
    ) -> None:
        self._leads = lead_service
        self._identity = identity_service
        self._questions = question_service or QuestionService()
        self._recommendations = recommendation_service

    def get_context(self, lead_id: UUID) -> VoiceContextResponse:
        lead = self._leads.get_lead(lead_id)
        next_response = self._questions.get_next_question(lead)
        progress = compute_profile_progress(lead)
        profile_completed = bool(next_response.completed)
        display_name = self._display_name(lead)
        opening = self._opening_message(lead, display_name)
        warnings: list[str] = []
        if lead.identity_verified is False and lead.known_lead:
            warnings.append(
                "La identidad no está verificada en este prototipo (sin OTP)."
            )
        return VoiceContextResponse(
            lead_id=lead.id,
            known_lead=bool(lead.known_lead),
            display_name=display_name,
            identity_status=(
                lead.identity_status.value
                if hasattr(lead.identity_status, "value")
                else str(lead.identity_status)
            ),
            profile_completed=profile_completed,
            progress=progress,
            next_question=next_response.next_question,
            upcoming_questions=self._questions.list_upcoming_questions(lead, limit=2),
            conversation_opening=opening,
            confirmed_fields=self._confirmed_fields(lead),
            fields_to_confirm=list(lead.fields_to_confirm),
            warnings=warnings,
            demo_mode=bool(lead.demo_mode),
        )

    def report_engagement(
        self,
        lead_id: UUID,
        payload: VoiceEngagementRequest,
    ) -> VoiceEngagementResponse:
        label = EngagementLabel(payload.label)
        saved = self._leads.apply_lead_updates(
            lead_id,
            {
                "engagement_label": label,
                "engagement_score": payload.score,
                "engagement_reason": (payload.reason or "").strip() or None,
                "engagement_updated_at": datetime.now(UTC),
                "fecha_actualizacion": datetime.now(UTC),
            },
        )
        return VoiceEngagementResponse(
            accepted=True,
            engagement_label=(
                saved.engagement_label.value
                if saved.engagement_label is not None
                else label.value
            ),
            engagement_score=saved.engagement_score,
            engagement_reason=saved.engagement_reason,
            engagement_updated_at=(
                saved.engagement_updated_at.isoformat()
                if saved.engagement_updated_at
                else None
            ),
        )

    def ensure_engagement(
        self,
        lead_id: UUID,
        *,
        label: str | None = None,
        score: int | None = None,
        reason: str | None = None,
        fallback_label: str = "desconocido",
        fallback_score: int = 50,
        fallback_reason: str = (
            "Cierre sin reporte explícito de predisposición; se registró por defecto."
        ),
        overwrite: bool = False,
    ) -> VoiceEngagementResponse | None:
        """Persist engagement at close. Uses provided values or a safe fallback."""
        lead = self._leads.get_lead(lead_id)
        if lead.engagement_label is not None and not overwrite and not label:
            return None

        resolved_label = (label or "").strip() or fallback_label
        try:
            EngagementLabel(resolved_label)
        except ValueError:
            resolved_label = fallback_label

        resolved_score = score if isinstance(score, int) else fallback_score
        resolved_reason = (reason or "").strip() or fallback_reason
        return self.report_engagement(
            lead_id,
            VoiceEngagementRequest(
                label=resolved_label,  # type: ignore[arg-type]
                score=max(0, min(100, resolved_score)),
                reason=resolved_reason,
            ),
        )

    def submit_answer(
        self,
        lead_id: UUID,
        payload: VoiceAnswerRequest,
    ) -> VoiceAnswerResponse:
        lead = self._leads.get_lead(lead_id)
        next_response = self._questions.get_next_question(lead)
        if next_response.completed or next_response.next_question is None:
            return VoiceAnswerResponse(
                accepted=False,
                profile_completed=True,
                progress=100,
                clarification_required=False,
                assistant_guidance=(
                    "El perfil ya está completo. Finaliza la orientación."
                ),
                validation_message="No hay preguntas pendientes.",
            )

        expected = next_response.next_question
        if payload.field != expected.field:
            return VoiceAnswerResponse(
                accepted=False,
                clarification_required=True,
                assistant_guidance=(
                    f"Continúa con la pregunta actual sobre {expected.field}."
                ),
                validation_message=(
                    "El campo enviado no coincide con la pregunta activa."
                ),
                next_question=expected,
                progress=compute_profile_progress(lead),
            )

        if payload.action == "skip" and expected.required:
            return VoiceAnswerResponse(
                accepted=False,
                clarification_required=True,
                assistant_guidance="Esta pregunta es necesaria para continuar.",
                validation_message="No se puede omitir esta pregunta.",
                next_question=expected,
                progress=compute_profile_progress(lead),
            )

        # Proyecto opcional: "lo que me recomiendes" / skip no debe trabar el flujo.
        if expected.field == "proyecto_interes" and (
            payload.action == "skip"
            or self._looks_like_project_deferral(payload.raw_transcript)
        ):
            payload = payload.model_copy(
                update={
                    "action": "answer",
                    "normalized_value": "sin preferencia",
                    "raw_transcript": payload.raw_transcript
                    or "sin preferencia",
                }
            )
        elif self._looks_like_non_answer_transcript(payload.raw_transcript):
            is_question = self._looks_like_user_question(payload.raw_transcript)
            return VoiceAnswerResponse(
                accepted=False,
                clarification_required=True,
                assistant_guidance=(
                    "El usuario pregunta. Contesta en 1–2 frases cortas y retoma "
                    f"la pregunta activa ({expected.field}). Sin menús ni esperas."
                    if is_question
                    else (
                        "No fue una respuesta usable. Repregunta en una frase corta "
                        f"el campo {expected.field}. Sin 'un segundo' ni menús."
                    )
                ),
                validation_message=(
                    "El transcript no parece una respuesta válida a la pregunta activa."
                ),
                next_question=expected,
                progress=compute_profile_progress(lead),
            )

        try:
            if expected.type == QuestionFieldType.CONFIRMATION:
                lead = self._apply_confirmation(lead, expected, payload)
            else:
                lead = self._apply_answer(lead, expected, payload)
        except ValidationBusinessError as exc:
            return VoiceAnswerResponse(
                accepted=False,
                clarification_required=True,
                assistant_guidance=self._clarification_for(expected),
                validation_message=exc.message,
                next_question=expected,
                progress=compute_profile_progress(lead),
            )

        refreshed = self._leads.get_lead(lead.id)
        following = self._questions.get_next_question(refreshed)
        upcoming = self._questions.list_upcoming_questions(refreshed, limit=2)
        progress = compute_profile_progress(refreshed)
        completed = bool(following.completed)
        guidance = (
            "Perfil completo. Llama complete_voice_profile y lee solo el cierre."
            if completed
            else self._guidance_for(following.next_question)
        )
        return VoiceAnswerResponse(
            accepted=True,
            updated_field=payload.field,
            profile_completed=completed,
            progress=progress,
            next_question=following.next_question,
            upcoming_questions=upcoming,
            assistant_guidance=guidance,
            warnings=[],
        )

    def complete(
        self,
        lead_id: UUID,
        payload: VoiceCompleteRequest | None = None,
    ) -> VoiceCompleteResponse:
        lead = self._leads.get_lead(lead_id)
        next_response = self._questions.get_next_question(lead)
        if not next_response.completed:
            raise ValidationBusinessError(
                "Aún faltan preguntas prioritarias por completar.",
                code="profile_incomplete",
            )

        engagement = self.ensure_engagement(
            lead_id,
            label=payload.engagement_label if payload else None,
            score=payload.engagement_score if payload else None,
            reason=payload.engagement_reason if payload else None,
            fallback_reason=(
                "Perfil cerrado sin predisposición explícita del agente; "
                "se registró por defecto al completar."
            ),
            overwrite=bool(payload and payload.engagement_label),
        )

        readiness = self._leads.evaluate(lead_id)
        recommendations = None
        top_project: dict[str, str] | None = None
        recommendations_count = 0
        spoken_summary: str | None = None
        recommended_projects: list[dict[str, object]] = []
        profile_json_path: str | None = None
        engine: str | None = None
        if self._recommendations is not None:
            refreshed = self._leads.get_lead(lead_id)
            try:
                recommendations = self._recommendations.recommend_for_lead(
                    refreshed,
                    limit=3,
                    persist_profile=True,
                    brochure_only=True,
                )
                recommendations_count = len(recommendations.recommended_projects)
                spoken_summary = recommendations.spoken_summary
                profile_json_path = recommendations.profile_json_path
                engine = recommendations.engine
                recommended_projects = [
                    {
                        "project_name": item.project_name,
                        "reason": item.reason,
                        "probability": item.probability,
                        "compatibility_score": item.compatibility_score,
                        "brochure_url": item.brochure_url,
                        "rank": item.rank,
                    }
                    for item in recommendations.recommended_projects
                ]
                if recommendations.recommended_projects:
                    first = recommendations.recommended_projects[0]
                    top_project = {
                        "id": first.canonical_project_id,
                        "name": first.project_name,
                        "reason": first.reason or "",
                        "brochure_url": first.brochure_url or "",
                    }
                    try:
                        self._leads.apply_commercial_from_recommendations(
                            lead_id,
                            recommendations,
                            persist=False,
                        )
                    except Exception:  # noqa: BLE001
                        pass
            except Exception:  # noqa: BLE001
                # El cierre de voz no debe fallar solo porque el recomendador tarde o falle.
                recommendations = None
                spoken_summary = (
                    "Ya tengo tu perfil listo. En la pantalla de resultados "
                    "vas a ver las opciones recomendadas en un momento."
                )
                engine = "deferred"

        closing = (
            "Ya terminé de construir tu perfil. "
            f"Encontré {recommendations_count} opciones que pueden ajustarse a ti."
        )
        if recommendations_count == 0:
            closing = "Ya terminé de construir tu perfil."
        elif recommendations_count == 1:
            closing = (
                "Ya terminé de construir tu perfil. "
                "Encontré una opción que puede ajustarse a ti."
            )
        elif recommendations_count == 3:
            closing = (
                "Ya terminé de construir tu perfil. "
                "Encontré tres opciones que pueden ajustarse a ti."
            )
        if spoken_summary:
            # Preferir el texto oral completo de Laura sin reescribirlo (evita cortes raros en TTS).
            closing = spoken_summary.strip()
            if closing and not closing.lower().startswith("según la charla"):
                closing = (
                    "Según la charla que tuve contigo, "
                    f"{closing[0].lower() + closing[1:] if closing else closing}"
                )

        # Persist completed profile into the configured repository (Postgres when enabled).
        try:
            self._leads.save_profile(lead_id)
        except Exception:  # noqa: BLE001
            pass

        refreshed = self._leads.get_lead(lead_id)
        return VoiceCompleteResponse(
            completed=True,
            readiness={
                "score": readiness.readiness_score,
                "status": readiness.status,
                "confidence": readiness.confidence,
            },
            recommendations_count=recommendations_count,
            top_project=top_project,
            next_action=readiness.next_action,
            navigation_path=f"/results/{lead_id}",
            assistant_closing=closing,
            disclaimer=readiness.disclaimer,
            spoken_summary=spoken_summary,
            recommended_projects=recommended_projects,
            profile_json_path=profile_json_path,
            engine=engine,
            engagement_label=(
                engagement.engagement_label
                if engagement is not None
                else (
                    refreshed.engagement_label.value
                    if refreshed.engagement_label is not None
                    else None
                )
            ),
            engagement_score=(
                engagement.engagement_score
                if engagement is not None
                else refreshed.engagement_score
            ),
            engagement_reason=(
                engagement.engagement_reason
                if engagement is not None
                else refreshed.engagement_reason
            ),
        )

    def _apply_confirmation(
        self,
        lead: Lead,
        question: NextQuestion,
        payload: VoiceAnswerRequest,
    ) -> Lead:
        confirmed = payload.action == "confirm" or (
            payload.action == "answer" and self._as_bool(payload.normalized_value) is True
        )
        if payload.action == "correct":
            confirmed = False
        confirmations = {
            question.field: {
                "confirmed": confirmed,
                "new_value": None if confirmed else payload.normalized_value,
            }
        }
        if not confirmed and payload.normalized_value is None:
            raise ValidationBusinessError(
                "Para corregir el dato necesitamos el nuevo valor.",
                code="missing_correction_value",
            )
        if not confirmed:
            confirmations[question.field]["new_value"] = self._coerce_value(
                question.field,
                question.type,
                payload.normalized_value,
            )
        return self._identity.confirm_prefilled_data(lead, confirmations)

    def _apply_answer(
        self,
        lead: Lead,
        question: NextQuestion,
        payload: VoiceAnswerRequest,
    ) -> Lead:
        if payload.action == "skip":
            # Campos opcionales deben quedar "respondidos" para no repetir la pregunta.
            if not question.required and question.field == "proyecto_interes":
                return self._leads.apply_lead_updates(
                    lead.id,
                    {
                        "proyecto_interes": "sin preferencia",
                        "field_metadata": {
                            "proyecto_interes": FieldProvenance(
                                source=DataSource.USER_DECLARED,
                                confirmed=True,
                                requires_confirmation=False,
                                updated_at=datetime.now(UTC),
                                previous_value=getattr(lead, "proyecto_interes", None),
                            )
                        },
                    },
                )
            return lead
        value = self._coerce_value(
            question.field,
            question.type,
            payload.normalized_value,
        )
        try:
            return self._leads.apply_lead_updates(
                lead.id,
                {
                    question.field: value,
                    "field_metadata": {
                        question.field: FieldProvenance(
                            source=DataSource.USER_DECLARED,
                            confirmed=True,
                            requires_confirmation=False,
                            updated_at=datetime.now(UTC),
                            previous_value=getattr(lead, question.field, None),
                        )
                    },
                },
            )
        except ValidationError as exc:
            raise ValidationBusinessError(
                "No pude guardar esa respuesta. ¿Puedes reformularla?",
                code="invalid_lead_update",
            ) from exc

    def _coerce_value(
        self,
        field: str,
        question_type: QuestionFieldType,
        value: Any,
    ) -> Any:
        if question_type in {QuestionFieldType.CURRENCY} or field in CURRENCY_FIELDS:
            number = self._as_number(value)
            if number is None:
                raise ValidationBusinessError("Necesitamos un valor numérico válido.")
            if number < 0:
                raise ValidationBusinessError(
                    "El valor debe ser mayor o igual a cero.",
                    code="negative_value",
                )
            return number
        if question_type == QuestionFieldType.INTEGER or field in INTEGER_FIELDS:
            number = self._as_number(value)
            if number is None:
                raise ValidationBusinessError("Necesitamos un número entero válido.")
            if number < 0:
                raise ValidationBusinessError(
                    "El valor debe ser mayor o igual a cero.",
                    code="negative_value",
                )
            return int(number)
        if (
            question_type
            in {QuestionFieldType.BOOLEAN, QuestionFieldType.CONSENT}
            or field in BOOLEAN_FIELDS
        ):
            parsed = self._as_bool(value)
            if parsed is None:
                raise ValidationBusinessError("Responde sí o no, por favor.")
            return parsed
        if field == "situacion_crediticia" or (
            question_type == QuestionFieldType.ENUM and field == "situacion_crediticia"
        ):
            return self._coerce_credit_situation(value)
        if field == "plazo_compra" or (
            question_type == QuestionFieldType.ENUM and field == "plazo_compra"
        ):
            return self._coerce_purchase_timeline(value)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValidationBusinessError("Necesitamos una respuesta para continuar.")
        return value

    @classmethod
    def _coerce_credit_situation(cls, value: Any) -> CreditSituation:
        if isinstance(value, CreditSituation):
            return value
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValidationBusinessError(
                "Indica tu situación crediticia, por ejemplo: sin reportes, al día o atrasos menores."
            )
        key = str(value).strip().lower()
        mapped = CREDIT_SITUATION_ALIASES.get(key)
        if mapped is not None:
            return mapped
        try:
            return CreditSituation(key)
        except ValueError as exc:
            raise ValidationBusinessError(
                "No reconocí esa situación crediticia. "
                "Puedes decir: sin reportes, al día, atrasos menores, atrasos mayores "
                "o que no estás seguro(a).",
                code="invalid_enum_value",
            ) from exc

    @classmethod
    def _coerce_purchase_timeline(cls, value: Any) -> PurchaseTimeline:
        if isinstance(value, PurchaseTimeline):
            return value
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValidationBusinessError(
                "Indica en cuánto tiempo te gustaría comprar, por ejemplo: de inmediato o en 6 meses."
            )
        key = str(value).strip().lower()
        mapped = PURCHASE_TIMELINE_ALIASES.get(key)
        if mapped is not None:
            return mapped
        try:
            return PurchaseTimeline(key)
        except ValueError as exc:
            raise ValidationBusinessError(
                "No reconocí ese plazo. "
                "Puedes decir: de inmediato, en 3 meses, en 6 meses, en 12 meses "
                "o que aún no lo defines.",
                code="invalid_enum_value",
            ) from exc

    @staticmethod
    def _as_number(value: Any) -> float | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            digits = (
                value.replace("$", "")
                .replace(".", "")
                .replace(",", ".")
                .replace(" ", "")
            )
            # Prefer Colombian thousand dots: strip non-digits.
            cleaned = "".join(ch for ch in value if ch.isdigit() or ch == "-")
            if cleaned in {"", "-"}:
                try:
                    return float(digits)
                except ValueError:
                    return None
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None

    @staticmethod
    def _looks_like_user_question(raw: str | None) -> bool:
        """Detect real user doubts — avoid false positives on answers with 'cuánto'."""
        if raw is None:
            return False
        text = raw.strip().lower()
        if not text:
            return False
        if "?" in text or "¿" in text:
            return True
        # Frases claras de duda (no bastan palabras sueltas tipo "cuánto"/"dónde").
        doubt_phrases = (
            "una duda",
            "tengo una duda",
            "una pregunta",
            "tengo una pregunta",
            "qué significa",
            "que significa",
            "no entend",
            "no te entend",
            "puedes repetir",
            "puedes explicar",
            "me puedes explicar",
            "quiero saber",
            "quisiera saber",
            "qué quieres decir",
            "que quieres decir",
            "me recomiendas algo",
            "qué me recomiendas",
            "que me recomiendas",
            "hay forma de",
            "cómo funciona",
            "como funciona",
            "qué es eso",
            "que es eso",
            "aclara",
            "explica un poco",
        )
        if any(phrase in text for phrase in doubt_phrases):
            return True
        # Solo al inicio, y si no parece respuesta (números / sí-no / montos).
        if re.match(
            r"^(qué|que|cómo|como|cuánto|cuanto|dónde|donde|cuál|cual|por\s*qué|por\s*que)\b",
            text,
        ):
            if re.search(
                r"\d|mill[oó]n|mil\b|pesos|s[ií]\b|\bno\b|aprox|alrededor",
                text,
            ):
                return False
            return True
        return False

    @staticmethod
    def _looks_like_non_answer_transcript(raw: str | None) -> bool:
        """Reject clear questions/fillers before persisting a voice answer."""
        if raw is None:
            return False
        text = raw.strip().lower()
        if not text:
            return True
        if VoiceOrchestrationService._looks_like_user_question(text):
            return True
        fillers = {
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
        return text in fillers

    @staticmethod
    def _as_bool(value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and value in {0, 1}:
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"si", "sí", "yes", "true", "correcto", "confirma"}:
                return True
            if normalized in {"no", "false", "incorrecto"}:
                return False
        return None

    @staticmethod
    def _display_name(lead: Lead) -> str | None:
        if not lead.nombre:
            return None
        return lead.nombre.split(" ")[0]

    @staticmethod
    def _opening_message(lead: Lead, display_name: str | None) -> str:
        name = display_name or ""
        hello = f"Hola {name}" if name else "Hola"
        if lead.known_lead and lead.afiliado:
            return (
                f"{hello}, soy Laura, asesora de Colsubsidio. "
                "Para orientarte bien con vivienda, te haré unas preguntas cortas; "
                "toma más o menos dos o tres minutos. "
                "¿Te parece si lo hacemos ahora, o prefieres más tarde?"
            )
        if lead.known_lead and lead.afiliado is False:
            return (
                f"{hello}, soy Laura, asesora de Colsubsidio. "
                "Te acompaño a mirar opciones de vivienda con unas preguntas sencillas; "
                "son como dos o tres minutos. "
                "¿Te late hacerlo ahora, o lo dejamos para después?"
            )
        return (
            f"{hello}, soy Laura, asesora de Colsubsidio. "
            "Quiero ayudarte a escoger vivienda con una charla corta: "
            "unas preguntas sencillas, más o menos dos o tres minutos. "
            "¿Te parece si arrancamos ahora, o prefieres más tarde?"
        )

    @staticmethod
    def _looks_like_project_deferral(raw: str | None) -> bool:
        if raw is None:
            return False
        text = raw.strip().lower()
        if not text:
            return False
        phrases = (
            "lo que me recomiend",
            "lo que tu recomiend",
            "lo que tú recomiend",
            "tú decides",
            "tu decides",
            "como veas",
            "como tú veas",
            "como tu veas",
            "da igual",
            "el que sea",
            "la que sea",
            "no tengo",
            "ninguno",
            "ninguna",
            "no sé",
            "no se",
            "sin preferencia",
            "me da igual",
            "tú me orient",
            "tu me orient",
            "que me orientes",
            "qué me orientes",
            "abierto",
            "después me dices",
            "lo que haya",
        )
        return any(p in text for p in phrases)

    @staticmethod
    def _confirmed_fields(lead: Lead) -> list[str]:
        confirmed: list[str] = []
        for field, meta in lead.field_metadata.items():
            if meta.confirmed and not meta.requires_confirmation:
                confirmed.append(field)
        return confirmed

    @staticmethod
    def _guidance_for(question: NextQuestion | None) -> str:
        if question is None:
            return "Di la siguiente pregunta corta del next_question."
        return (
            "Di SOLO la siguiente pregunta en ≤12 palabras (reformulada, sencilla). "
            f"Campo activo: {question.field}. Intención: {question.question}. "
            "Prohibido: muletillas, eco, 'un segundo', 'voy a analizar', menús."
        )

    @staticmethod
    def _clarification_for(question: NextQuestion) -> str:
        if question.type == QuestionFieldType.CURRENCY:
            return "Pide nuevamente el valor en pesos colombianos."
        if question.type == QuestionFieldType.BOOLEAN:
            return "Pide una respuesta clara de sí o no."
        return "Reformula brevemente la pregunta actual."
