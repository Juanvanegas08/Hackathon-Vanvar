"""Lead domain model and related enums."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class LeadStatus(StrEnum):
    """Lifecycle states for a lead profile."""

    NUEVO = "nuevo"
    PERFIL_INCOMPLETO = "perfil_incompleto"
    LISTO_PARA_ASESOR = "listo_para_asesor"
    RUTA_NUTRICION = "ruta_nutricion"
    NO_AFILIADO_EN_EVALUACION = "no_afiliado_en_evaluacion"
    REQUIERE_REVISION = "requiere_revision"


class CanalOrigen(StrEnum):
    """Known acquisition channels."""

    PAUTA_DIGITAL = "pauta_digital"
    REDES_SOCIALES = "redes_sociales"
    FORMULARIO = "formulario"
    WHATSAPP = "whatsapp"
    REFERIDO = "referido"
    OTRO = "otro"
    DESCONOCIDO = "desconocido"


class AffiliationCategory(StrEnum):
    """Colsubsidio affiliation salary categories A/B/C/D."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"


class PurchaseTimeline(StrEnum):
    """Estimated purchase window declared by the lead."""

    INMEDIATO = "inmediato"
    TRES_MESES = "3_meses"
    SEIS_MESES = "6_meses"
    DOCE_MESES = "12_meses"
    MAS_DE_UN_ANO = "mas_de_un_ano"
    NO_DEFINIDO = "no_definido"


class CreditSituation(StrEnum):
    """Self-declared credit situation (not an official bureau result)."""

    SIN_REPORTES = "sin_reportes"
    AL_DIA = "al_dia"
    ATRASOS_MENORES = "atrasos_menores"
    ATRASOS_MAYORES = "atrasos_mayores"
    EN_PROCESO_NORMALIZACION = "en_proceso_normalizacion"
    DESCONOCIDA = "desconocida"


class QuestionFieldType(StrEnum):
    """Supported answer types for profiling questions."""

    BOOLEAN = "boolean"
    CURRENCY = "currency"
    INTEGER = "integer"
    TEXT = "text"
    ENUM = "enum"
    CONSENT = "consent"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Lead(BaseModel):
    """In-memory lead profile used by profiling services."""

    model_config = ConfigDict(from_attributes=True, use_enum_values=False)

    id: UUID = Field(default_factory=uuid4)
    nombre: str | None = None
    telefono: str | None = None
    correo: EmailStr | None = None
    canal_origen: CanalOrigen = CanalOrigen.DESCONOCIDO
    consentimiento: bool | None = None
    afiliado: bool | None = None
    afiliacion_confirmada: bool = False
    categoria_afiliacion: AffiliationCategory | None = None
    empresa: str | None = None
    salario_mensual: float | None = None
    ingreso_hogar: float | None = None
    ahorro: float | None = None
    obligaciones_mensuales: float | None = None
    tiene_vivienda: bool | None = None
    personas_hogar: int | None = None
    personas_a_cargo: int | None = None
    beneficiarios_registrados: int | None = None
    situacion_crediticia: CreditSituation | None = None
    ubicacion_actual: str | None = None
    ubicacion_deseada: str | None = None
    plazo_compra: PurchaseTimeline | None = None
    proyecto_interes: str | None = None
    estado_lead: LeadStatus = LeadStatus.NUEVO
    fecha_creacion: datetime = Field(default_factory=_utcnow)
    fecha_actualizacion: datetime = Field(default_factory=_utcnow)

    @field_validator(
        "salario_mensual",
        "ingreso_hogar",
        "ahorro",
        "obligaciones_mensuales",
    )
    @classmethod
    def non_negative_money(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("Los valores monetarios no pueden ser negativos")
        return value

    @field_validator("personas_hogar", "personas_a_cargo", "beneficiarios_registrados")
    @classmethod
    def non_negative_counts(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("Los conteos de personas no pueden ser negativos")
        return value

    def apply_partial_update(self, data: dict[str, Any]) -> "Lead":
        """Merge non-None fields without clearing previously known valid values."""
        updates = {key: value for key, value in data.items() if value is not None}
        if not updates:
            return self
        updates["fecha_actualizacion"] = _utcnow()
        return self.model_copy(update=updates)
