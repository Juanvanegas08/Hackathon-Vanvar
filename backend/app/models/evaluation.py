"""Evaluation domain result models."""

from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.lead import AffiliationCategory, LeadStatus


class CategorySource(StrEnum):
    """How an affiliation category was obtained."""

    CALCULADA = "calculada"
    DECLARADA = "declarada"
    SISTEMA = "sistema"
    INDETERMINADA = "indeterminada"


class ConfidenceLevel(StrEnum):
    """Confidence in the readiness assessment."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AffiliationCategoryResult(BaseModel):
    """Result of affiliation category calculation."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "afiliado": True,
                    "categoria": "A",
                    "salario_mensual": 2500000,
                    "salario_en_smmlv": 1.75,
                    "fuente": "calculada",
                    "requiere_confirmacion": True,
                }
            ]
        }
    )

    afiliado: bool | None
    categoria: AffiliationCategory | None
    salario_mensual: float | None = None
    salario_en_smmlv: Decimal | None = None
    fuente: CategorySource = CategorySource.CALCULADA
    requiere_confirmacion: bool = True


class ReadinessResult(BaseModel):
    """Preliminary purchase-readiness / profile-completeness evaluation."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "lead_id": "00000000-0000-0000-0000-000000000001",
                    "readiness_score": 78,
                    "confidence": "medium",
                    "status": "listo_para_asesor",
                    "complete_fields": ["afiliado", "salario_mensual", "ahorro"],
                    "missing_fields": ["situacion_crediticia"],
                    "positive_factors": ["Afiliación identificada", "Cuenta con ahorro"],
                    "gaps": ["Falta confirmar la situación crediticia"],
                    "next_action": (
                        "Completar la situación crediticia y preparar contacto comercial"
                    ),
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
    readiness_score: int = Field(ge=0, le=100)
    confidence: ConfidenceLevel
    status: LeadStatus
    complete_fields: list[str]
    missing_fields: list[str]
    positive_factors: list[str]
    gaps: list[str]
    next_action: str
    warnings: list[str] = Field(default_factory=list)
    disclaimer: str
