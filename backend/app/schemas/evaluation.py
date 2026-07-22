"""Evaluation and profiling API schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.evaluation import ConfidenceLevel
from app.models.lead import AffiliationCategory, LeadStatus, QuestionFieldType


class AffiliationCategoryRequest(BaseModel):
    """Input for affiliation category calculation endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "afiliado": True,
                    "salario_mensual": 2500000,
                    "afiliacion_confirmada": False,
                }
            ]
        }
    )

    afiliado: bool | None = None
    salario_mensual: float | None = Field(default=None, ge=0)
    afiliacion_confirmada: bool = False


class AffiliationCategoryResponse(BaseModel):
    """Output for affiliation category calculation endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "categoria": "A",
                    "salario_en_smmlv": 1.75,
                    "requiere_confirmacion": True,
                }
            ]
        }
    )

    categoria: AffiliationCategory | None
    salario_en_smmlv: float | None
    requiere_confirmacion: bool
    afiliado: bool | None = None
    salario_mensual: float | None = None
    fuente: str = "calculada"


class NextQuestion(BaseModel):
    """Structured next question for the voice agent / interviewer."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "field": "ahorro",
                    "question": (
                        "¿Actualmente cuentas con algún ahorro destinado "
                        "a la compra de vivienda?"
                    ),
                    "type": "currency",
                    "required": True,
                    "reason": (
                        "Necesitamos estimar tu capacidad y la posible "
                        "brecha de cuota inicial"
                    ),
                    "confirmation_required": False,
                }
            ]
        }
    )

    field: str
    question: str
    type: QuestionFieldType
    required: bool = True
    reason: str
    confirmation_required: bool = False


class NextQuestionResponse(BaseModel):
    """Response for next-question endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "completed": False,
                    "next_question": {
                        "field": "afiliado",
                        "question": "¿Estás afiliado(a) a Colsubsidio?",
                        "type": "boolean",
                        "required": True,
                        "reason": "La mayoría de ventas corresponde a afiliados",
                        "confirmation_required": True,
                    },
                },
                {"completed": True, "next_question": None},
            ]
        }
    )

    completed: bool
    next_question: NextQuestion | None = None


class ReadinessResponse(BaseModel):
    """Readiness evaluation response."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "lead_id": "00000000-0000-0000-0000-000000000001",
                    "readiness_score": 78,
                    "confidence": "medium",
                    "status": "listo_para_asesor",
                    "complete_fields": ["afiliado", "salario_mensual"],
                    "missing_fields": ["situacion_crediticia"],
                    "positive_factors": ["Afiliación identificada"],
                    "gaps": ["Falta confirmar la situación crediticia"],
                    "next_action": "Completar la situación crediticia",
                    "warnings": [],
                    "disclaimer": (
                        "Resultado orientativo. No constituye una aprobación "
                        "de crédito hipotecario."
                    ),
                }
            ]
        }
    )

    lead_id: UUID
    readiness_score: int
    confidence: ConfidenceLevel
    status: LeadStatus
    complete_fields: list[str]
    missing_fields: list[str]
    positive_factors: list[str]
    gaps: list[str]
    next_action: str
    warnings: list[str]
    disclaimer: str


class AffiliationSummaryBlock(BaseModel):
    is_affiliated: bool | None
    category: AffiliationCategory | None
    confirmed: bool


class FinancialProfileBlock(BaseModel):
    personal_income: float | None
    household_income: float | None
    savings: float | None
    monthly_obligations: float | None


class ReadinessSummaryBlock(BaseModel):
    score: int
    status: LeadStatus
    confidence: ConfidenceLevel


class AdvisorSummaryResponse(BaseModel):
    """Structured summary for a future commercial advisor."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "lead_id": "00000000-0000-0000-0000-000000000001",
                    "headline": "Lead afiliado con perfil avanzado",
                    "basic_data": {
                        "nombre": "Ana Pérez",
                        "telefono": "3001234567",
                        "correo": "ana@example.com",
                        "canal_origen": "whatsapp",
                    },
                    "affiliation": {
                        "is_affiliated": True,
                        "category": "A",
                        "confirmed": False,
                    },
                    "financial_profile": {
                        "personal_income": 2500000,
                        "household_income": 4200000,
                        "savings": 18000000,
                        "monthly_obligations": 500000,
                    },
                    "household": {
                        "personas_hogar": 3,
                        "personas_a_cargo": 1,
                        "tiene_vivienda": False,
                    },
                    "readiness": {
                        "score": 78,
                        "status": "listo_para_asesor",
                        "confidence": "medium",
                    },
                    "gaps": ["Falta confirmar la situación crediticia"],
                    "fields_to_confirm": ["afiliado", "salario_mensual"],
                    "recommended_projects": [],
                    "next_action": (
                        "Validar información pendiente y agendar conversación comercial"
                    ),
                    "disclaimer": (
                        "Resultado orientativo. No constituye una aprobación "
                        "de crédito hipotecario."
                    ),
                }
            ]
        }
    )

    lead_id: UUID
    headline: str
    basic_data: dict[str, str | None]
    affiliation: AffiliationSummaryBlock
    financial_profile: FinancialProfileBlock
    household: dict[str, int | bool | None]
    readiness: ReadinessSummaryBlock
    gaps: list[str]
    fields_to_confirm: list[str]
    recommended_projects: list[dict[str, object]] = Field(default_factory=list)
    next_action: str
    disclaimer: str
