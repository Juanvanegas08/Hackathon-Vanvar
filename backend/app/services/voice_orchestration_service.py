"""Voice orchestration services that wrap existing profiling logic."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.exceptions import ValidationBusinessError
from app.models.lead import DataSource, FieldProvenance, Lead, QuestionFieldType
from app.schemas.evaluation import NextQuestion
from app.schemas.realtime import (
    VoiceAnswerRequest,
    VoiceAnswerResponse,
    VoiceCompleteResponse,
    VoiceContextResponse,
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
            conversation_opening=opening,
            confirmed_fields=self._confirmed_fields(lead),
            fields_to_confirm=list(lead.fields_to_confirm),
            warnings=warnings,
            demo_mode=bool(lead.demo_mode),
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
        progress = compute_profile_progress(refreshed)
        completed = bool(following.completed)
        guidance = (
            "Agradece brevemente y finaliza el perfilamiento."
            if completed
            else self._guidance_for(following.next_question)
        )
        return VoiceAnswerResponse(
            accepted=True,
            updated_field=payload.field,
            profile_completed=completed,
            progress=progress,
            next_question=following.next_question,
            assistant_guidance=guidance,
            warnings=[],
        )

    def complete(self, lead_id: UUID) -> VoiceCompleteResponse:
        lead = self._leads.get_lead(lead_id)
        next_response = self._questions.get_next_question(lead)
        if not next_response.completed:
            raise ValidationBusinessError(
                "Aún faltan preguntas prioritarias por completar.",
                code="profile_incomplete",
            )

        readiness = self._leads.evaluate(lead_id)
        recommendations = None
        top_project: dict[str, str] | None = None
        recommendations_count = 0
        if self._recommendations is not None:
            refreshed = self._leads.get_lead(lead_id)
            recommendations = self._recommendations.recommend_for_lead(
                refreshed,
                limit=3,
            )
            recommendations_count = len(recommendations.recommended_projects)
            if recommendations.recommended_projects:
                first = recommendations.recommended_projects[0]
                top_project = {
                    "id": first.canonical_project_id,
                    "name": first.project_name,
                }

        closing = (
            "Ya terminé de construir tu perfil. "
            f"Encontré {recommendations_count or 'algunas'} opciones que pueden ajustarse a ti."
        )
        if recommendations_count == 1:
            closing = (
                "Ya terminé de construir tu perfil. "
                "Encontré una opción que puede ajustarse a ti."
            )
        elif recommendations_count == 3:
            closing = (
                "Ya terminé de construir tu perfil. "
                "Encontré tres opciones que pueden ajustarse a ti."
            )

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
            return lead
        value = self._coerce_value(
            question.field,
            question.type,
            payload.normalized_value,
        )
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
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValidationBusinessError("Necesitamos una respuesta para continuar.")
        return value

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
        name = display_name or "hola"
        if lead.known_lead and lead.afiliado:
            return (
                f"Hola, {name}. Ya conocemos una parte de tu perfil, "
                "así que esta conversación será más corta."
            )
        if lead.known_lead and lead.afiliado is False:
            return (
                f"Hola, {name}. Encontramos información básica y podemos "
                "construir juntos una orientación personalizada."
            )
        return (
            f"Hola{', ' + name if display_name else ''}. "
            "Vamos a construir tu perfil de vivienda en pocos minutos, "
            "con una pregunta a la vez."
        )

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
            return "Continúa con la siguiente pregunta del backend."
        if question.type == QuestionFieldType.CONFIRMATION:
            return (
                "Pide confirmación del dato precargado sin revelar cifras "
                "sensibles innecesarias."
            )
        return f"Agradece brevemente y pregunta: {question.question}"

    @staticmethod
    def _clarification_for(question: NextQuestion) -> str:
        if question.type == QuestionFieldType.CURRENCY:
            return "Pide nuevamente el valor en pesos colombianos."
        if question.type == QuestionFieldType.BOOLEAN:
            return "Pide una respuesta clara de sí o no."
        return "Reformula brevemente la pregunta actual."
