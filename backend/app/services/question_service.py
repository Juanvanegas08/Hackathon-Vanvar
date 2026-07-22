"""Rule-based next-question engine for lead profiling."""

from dataclasses import dataclass

from app.models.lead import Lead, QuestionFieldType
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


QUESTION_SEQUENCE: tuple[QuestionRule, ...] = (
    QuestionRule(
        field="consentimiento",
        question="¿Autorizas continuar con esta conversación para perfilar tu interés en vivienda?",
        type=QuestionFieldType.CONSENT,
        reason="Necesitamos tu consentimiento para continuar el perfilamiento",
        confirmation_required=False,
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


class QuestionService:
    """Determine the next highest-priority missing question without using an LLM."""

    def get_next_question(self, lead: Lead) -> NextQuestionResponse:
        """Return the next unanswered priority question or a completed marker."""
        for rule in QUESTION_SEQUENCE:
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
        return [
            rule.field
            for rule in QUESTION_SEQUENCE
            if self._is_field_missing(lead, rule.field) and rule.required
        ]

    def list_complete_fields(self, lead: Lead) -> list[str]:
        """Return completed profile fields from the question sequence."""
        return [
            rule.field
            for rule in QUESTION_SEQUENCE
            if not self._is_field_missing(lead, rule.field)
        ]

    @staticmethod
    def _is_field_missing(lead: Lead, field: str) -> bool:
        value = getattr(lead, field, None)
        if field == "personas_a_cargo":
            # Accept either dependents or registered beneficiaries as composition signal.
            return lead.personas_a_cargo is None and lead.beneficiarios_registrados is None
        if isinstance(value, str):
            return value.strip() == ""
        return value is None
