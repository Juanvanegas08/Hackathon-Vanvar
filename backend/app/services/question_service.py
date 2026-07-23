"""Rule-based next-question engine for lead profiling."""

from dataclasses import dataclass
from typing import Any

from app.models.lead import DataSource, Lead, QuestionFieldType
from app.schemas.evaluation import NextQuestion, NextQuestionResponse


@dataclass(frozen=True, slots=True)
class QuestionRule:
    """Definition of a prioritized profiling question."""

    field: str
    question: str
    type: QuestionFieldType
    reason: str
    required: bool = True
    confirmation_required: bool = False


NEW_LEAD_SEQUENCE: tuple[QuestionRule, ...] = (
    QuestionRule(
        field="consentimiento",
        question="¿Autorizas continuar con esta conversación para perfilar tu interés en vivienda?",
        type=QuestionFieldType.CONSENT,
        reason="Necesitamos tu consentimiento para continuar el perfilamiento",
    ),
    QuestionRule(
        field="afiliado",
        question="¿Estás afiliado(a) a Colsubsidio?",
        type=QuestionFieldType.BOOLEAN,
        reason="La mayoría de las ventas corresponde a personas afiliadas",
        confirmation_required=True,
    ),
    QuestionRule(
        field="salario_mensual",
        question="¿Cuál es tu salario mensual personal reportado por tu empleador?",
        type=QuestionFieldType.CURRENCY,
        reason="Permite calcular tu categoría de afiliación A, B o C",
        confirmation_required=True,
    ),
    QuestionRule(
        field="ingreso_hogar",
        question="¿Cuál es el ingreso total mensual de tu hogar?",
        type=QuestionFieldType.CURRENCY,
        reason="Ayuda a estimar la capacidad de compra del hogar",
        confirmation_required=True,
    ),
    QuestionRule(
        field="ahorro",
        question="¿Actualmente cuentas con algún ahorro destinado a la compra de vivienda?",
        type=QuestionFieldType.CURRENCY,
        reason="Necesitamos estimar tu capacidad y la posible brecha de cuota inicial",
        confirmation_required=True,
    ),
    QuestionRule(
        field="obligaciones_mensuales",
        question="¿Cuánto pagas aproximadamente cada mes en obligaciones financieras?",
        type=QuestionFieldType.CURRENCY,
        reason="Permite entender tu capacidad residual de pago",
        confirmation_required=True,
    ),
    QuestionRule(
        field="tiene_vivienda",
        question="¿Actualmente tienes vivienda propia?",
        type=QuestionFieldType.BOOLEAN,
        reason="La tenencia de vivienda afecta el enfoque comercial y de subsidios",
    ),
    QuestionRule(
        field="personas_hogar",
        question="¿Cuántas personas viven actualmente en tu hogar?",
        type=QuestionFieldType.INTEGER,
        reason="La composición del hogar orienta tipologías y capacidad",
    ),
    QuestionRule(
        field="personas_a_cargo",
        question="¿Cuántas personas tienes a cargo o como beneficiarios registrados?",
        type=QuestionFieldType.INTEGER,
        reason="Las personas a cargo influencian necesidades de vivienda",
    ),
    QuestionRule(
        field="situacion_crediticia",
        question="¿Cómo describirías tu situación crediticia actual?",
        type=QuestionFieldType.ENUM,
        reason="La situación crediticia declarada ayuda a orientar la conversación comercial",
        confirmation_required=True,
    ),
    QuestionRule(
        field="ubicacion_deseada",
        question="¿En qué zona o municipio te gustaría comprar vivienda?",
        type=QuestionFieldType.TEXT,
        reason="La ubicación deseada filtra proyectos compatibles",
    ),
    QuestionRule(
        field="plazo_compra",
        question="¿En qué plazo estimas comprar vivienda?",
        type=QuestionFieldType.ENUM,
        reason="El plazo define urgencia y ruta comercial",
    ),
    QuestionRule(
        field="proyecto_interes",
        question="¿Tienes algún proyecto o preferencia específica de interés?",
        type=QuestionFieldType.TEXT,
        reason="Las preferencias preparan la futura recomendación de proyectos",
        required=False,
    ),
)

KNOWN_LEAD_SEQUENCE: tuple[QuestionRule, ...] = (
    QuestionRule(
        field="consentimiento",
        question="¿Autorizas el uso de tu información para continuar el perfilamiento de vivienda?",
        type=QuestionFieldType.CONSENT,
        reason="Se requiere consentimiento para usar o confirmar datos precargados",
    ),
    QuestionRule(
        field="ingreso_hogar",
        question="¿Cuál es el ingreso total mensual de tu hogar?",
        type=QuestionFieldType.CURRENCY,
        reason="Ayuda a estimar la capacidad de compra del hogar",
        confirmation_required=True,
    ),
    QuestionRule(
        field="ahorro",
        question="¿Actualmente cuentas con algún ahorro destinado a la compra de vivienda?",
        type=QuestionFieldType.CURRENCY,
        reason="Necesitamos estimar tu capacidad y la posible brecha de cuota inicial",
        confirmation_required=True,
    ),
    QuestionRule(
        field="obligaciones_mensuales",
        question="¿Cuánto pagas aproximadamente cada mes en obligaciones financieras?",
        type=QuestionFieldType.CURRENCY,
        reason="Permite entender tu capacidad residual de pago",
        confirmation_required=True,
    ),
    QuestionRule(
        field="tiene_vivienda",
        question="¿Actualmente tienes vivienda propia?",
        type=QuestionFieldType.BOOLEAN,
        reason="La tenencia de vivienda afecta el enfoque comercial y de subsidios",
    ),
    QuestionRule(
        field="situacion_crediticia",
        question="¿Cómo describirías tu situación crediticia actual?",
        type=QuestionFieldType.ENUM,
        reason="La situación crediticia declarada ayuda a orientar la conversación comercial",
        confirmation_required=True,
    ),
    QuestionRule(
        field="ubicacion_deseada",
        question="¿En qué zona o municipio te gustaría comprar vivienda?",
        type=QuestionFieldType.TEXT,
        reason="La ubicación deseada filtra proyectos compatibles",
    ),
    QuestionRule(
        field="plazo_compra",
        question="¿En qué plazo estimas comprar vivienda?",
        type=QuestionFieldType.ENUM,
        reason="El plazo define urgencia y ruta comercial",
    ),
    QuestionRule(
        field="proyecto_interes",
        question="¿Tienes algún proyecto o preferencia específica de interés?",
        type=QuestionFieldType.TEXT,
        reason="Las preferencias preparan la futura recomendación de proyectos",
        required=False,
    ),
)

# Keep backward-compatible name used by older imports/tests.
QUESTION_SEQUENCE = NEW_LEAD_SEQUENCE


class QuestionService:
    """Determine the next highest-priority missing question without using an LLM."""

    def get_next_question(self, lead: Lead) -> NextQuestionResponse:
        """Return the next unanswered priority question or a completed marker."""
        if lead.data_consent is None and lead.consentimiento is None and lead.known_lead:
            return NextQuestionResponse(
                completed=False,
                next_question=NextQuestion(
                    field="data_consent",
                    question=(
                        "¿Autorizas el uso de tu información para continuar "
                        "el perfilamiento de vivienda?"
                    ),
                    type=QuestionFieldType.CONSENT,
                    required=True,
                    reason="Se requiere consentimiento para precargar o confirmar datos",
                    confirmation_required=False,
                ),
            )

        # Prefill confirmations first for known leads.
        for field in lead.fields_to_confirm:
            if lead.is_field_confirmed(field):
                continue
            return NextQuestionResponse(
                completed=False,
                next_question=self._confirmation_question(lead, field),
            )

        sequence = KNOWN_LEAD_SEQUENCE if lead.known_lead else NEW_LEAD_SEQUENCE
        for rule in sequence:
            if self._should_skip_for_known_lead(lead, rule.field):
                continue
            if self._is_field_missing(lead, rule.field):
                return NextQuestionResponse(
                    completed=False,
                    next_question=NextQuestion(
                        field=rule.field,
                        question=rule.question,
                        type=rule.type,
                        required=rule.required,
                        reason=rule.reason,
                        confirmation_required=rule.confirmation_required,
                    ),
                )
        return NextQuestionResponse(completed=True, next_question=None)

    def list_missing_fields(self, lead: Lead) -> list[str]:
        """Return missing fields in priority order."""
        missing = list(lead.fields_to_confirm)
        sequence = KNOWN_LEAD_SEQUENCE if lead.known_lead else NEW_LEAD_SEQUENCE
        for rule in sequence:
            if not rule.required:
                continue
            if self._should_skip_for_known_lead(lead, rule.field):
                continue
            if self._is_field_missing(lead, rule.field) and rule.field not in missing:
                missing.append(rule.field)
        return missing

    def list_complete_fields(self, lead: Lead) -> list[str]:
        """Return completed profile fields from the active question sequence."""
        sequence = KNOWN_LEAD_SEQUENCE if lead.known_lead else NEW_LEAD_SEQUENCE
        complete = [
            rule.field
            for rule in sequence
            if not self._is_field_missing(lead, rule.field)
        ]
        for field in lead.prefilled_fields:
            if field not in complete and not lead.field_requires_confirmation(field):
                complete.append(field)
        return complete

    def _confirmation_question(self, lead: Lead, field: str) -> NextQuestion:
        meta = lead.field_metadata.get(field)
        source = meta.source if meta else DataSource.MOCK_AFFILIATION_SERVICE
        current_value: Any = getattr(lead, field, None)
        if field == "salario_mensual":
            category = (
                lead.categoria_afiliacion.value
                if lead.categoria_afiliacion is not None
                else "registrada"
            )
            question = (
                f"Tenemos registrado un salario laboral dentro de la categoría "
                f"{category}. ¿Esta información sigue siendo correcta?"
            )
        elif field == "personas_a_cargo":
            question = (
                "Tenemos registradas personas a cargo o beneficiarios. "
                "¿Esta información sigue siendo correcta?"
            )
        elif field == "afiliado":
            question = (
                "Tenemos un estado de afiliación pendiente de confirmación. "
                "¿Confirmas que esta información es correcta?"
            )
        else:
            question = (
                f"Tenemos un valor precargado para {field}. "
                "¿Esta información sigue siendo correcta?"
            )
        return NextQuestion(
            field=field,
            question=question,
            type=QuestionFieldType.CONFIRMATION,
            required=True,
            reason="Dato precargado pendiente de confirmación",
            confirmation_required=True,
            current_value=current_value,
            source=source.value if hasattr(source, "value") else str(source),
        )

    def _should_skip_for_known_lead(self, lead: Lead, field: str) -> bool:
        if not lead.known_lead:
            return False
        # Never re-ask confirmed affiliation identity fields.
        if (
            field in {"afiliado", "empresa"}
            and field in lead.prefilled_fields
            and field not in lead.fields_to_confirm
        ):
            return True
        if field == "salario_mensual" and lead.is_field_confirmed("salario_mensual"):
            return True
        if field == "personas_a_cargo" and lead.is_field_confirmed("personas_a_cargo"):
            return True
        return field == "categoria_afiliacion"

    @staticmethod
    def _is_field_missing(lead: Lead, field: str) -> bool:
        if field == "consentimiento":
            return lead.consentimiento is None and lead.data_consent is None
        if field == "data_consent":
            return lead.data_consent is None
        value = getattr(lead, field, None)
        if field == "personas_a_cargo":
            return lead.personas_a_cargo is None and lead.beneficiarios_registrados is None
        if isinstance(value, str):
            return value.strip() == ""
        return value is None
