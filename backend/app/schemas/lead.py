"""Lead API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.lead import (
    AffiliationCategory,
    CanalOrigen,
    CreditSituation,
    Lead,
    LeadStatus,
    PurchaseTimeline,
)


class LeadCreate(BaseModel):
    """Payload to create a lead."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "nombre": "Ana Pérez",
                    "telefono": "3001234567",
                    "correo": "ana@example.com",
                    "canal_origen": "whatsapp",
                    "consentimiento": True,
                    "afiliado": True,
                }
            ]
        }
    )

    nombre: str | None = None
    telefono: str | None = None
    correo: EmailStr | None = None
    canal_origen: CanalOrigen = CanalOrigen.DESCONOCIDO
    consentimiento: bool | None = None
    afiliado: bool | None = None
    afiliacion_confirmada: bool = False
    categoria_afiliacion: AffiliationCategory | None = None
    empresa: str | None = None
    salario_mensual: float | None = Field(default=None, ge=0)
    ingreso_hogar: float | None = Field(default=None, ge=0)
    ahorro: float | None = Field(default=None, ge=0)
    obligaciones_mensuales: float | None = Field(default=None, ge=0)
    tiene_vivienda: bool | None = None
    personas_hogar: int | None = Field(default=None, ge=0)
    personas_a_cargo: int | None = Field(default=None, ge=0)
    beneficiarios_registrados: int | None = Field(default=None, ge=0)
    situacion_crediticia: CreditSituation | None = None
    ubicacion_actual: str | None = None
    ubicacion_deseada: str | None = None
    plazo_compra: PurchaseTimeline | None = None
    proyecto_interes: str | None = None
    estado_lead: LeadStatus = LeadStatus.NUEVO


class LeadUpdate(BaseModel):
    """Partial update payload. Omitted/null fields do not clear existing values."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "salario_mensual": 2500000,
                    "ahorro": 18000000,
                    "ubicacion_deseada": "Bogotá",
                }
            ]
        }
    )

    nombre: str | None = None
    telefono: str | None = None
    correo: EmailStr | None = None
    canal_origen: CanalOrigen | None = None
    consentimiento: bool | None = None
    afiliado: bool | None = None
    afiliacion_confirmada: bool | None = None
    categoria_afiliacion: AffiliationCategory | None = None
    empresa: str | None = None
    salario_mensual: float | None = Field(default=None, ge=0)
    ingreso_hogar: float | None = Field(default=None, ge=0)
    ahorro: float | None = Field(default=None, ge=0)
    obligaciones_mensuales: float | None = Field(default=None, ge=0)
    tiene_vivienda: bool | None = None
    personas_hogar: int | None = Field(default=None, ge=0)
    personas_a_cargo: int | None = Field(default=None, ge=0)
    beneficiarios_registrados: int | None = Field(default=None, ge=0)
    situacion_crediticia: CreditSituation | None = None
    ubicacion_actual: str | None = None
    ubicacion_deseada: str | None = None
    plazo_compra: PurchaseTimeline | None = None
    proyecto_interes: str | None = None
    estado_lead: LeadStatus | None = None

    @field_validator(
        "salario_mensual",
        "ingreso_hogar",
        "ahorro",
        "obligaciones_mensuales",
        "personas_hogar",
        "personas_a_cargo",
        "beneficiarios_registrados",
    )
    @classmethod
    def reject_negative(cls, value: float | int | None) -> float | int | None:
        if value is not None and value < 0:
            raise ValueError("El valor no puede ser negativo")
        return value


class LeadResponse(BaseModel):
    """Lead response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nombre: str | None
    telefono: str | None
    correo: EmailStr | None
    canal_origen: CanalOrigen
    consentimiento: bool | None
    afiliado: bool | None
    afiliacion_confirmada: bool
    categoria_afiliacion: AffiliationCategory | None
    empresa: str | None
    salario_mensual: float | None
    ingreso_hogar: float | None
    ahorro: float | None
    obligaciones_mensuales: float | None
    tiene_vivienda: bool | None
    personas_hogar: int | None
    personas_a_cargo: int | None
    beneficiarios_registrados: int | None
    situacion_crediticia: CreditSituation | None
    ubicacion_actual: str | None
    ubicacion_deseada: str | None
    plazo_compra: PurchaseTimeline | None
    proyecto_interes: str | None
    estado_lead: LeadStatus
    fecha_creacion: datetime
    fecha_actualizacion: datetime

    @classmethod
    def from_lead(cls, lead: Lead) -> "LeadResponse":
        return cls.model_validate(lead)
