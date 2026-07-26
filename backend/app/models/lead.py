"""Lead domain model and related enums."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.utils.commercial_affinity import AffinityBand
from app.utils.email import sanitize_optional_email


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


class EngagementLabel(StrEnum):
    """Dominant user sentiment / tone for advisor follow-up (web + phone).

    Pick the PRIMARY signal that best helps the human advisor approach the lead.
    Emotion and courtesy beat generic commercial labels when clear.
    """

    FELIZ = "feliz"
    TRISTE = "triste"
    ENOJADO = "enojado"
    CONSTERNADO = "consternado"
    GROSERO = "grosero"
    CORTES = "cortes"
    INTERESADO = "interesado"
    INDECISO = "indeciso"
    MOLESTO = "molesto"  # legacy alias ≈ enojado
    TROLLEANDO = "trolleando"
    OCUPADO = "ocupado"
    DESCONOCIDO = "desconocido"


ENGAGEMENT_LABEL_VALUES: tuple[str, ...] = tuple(label.value for label in EngagementLabel)


class QuestionFieldType(StrEnum):
    """Supported answer types for profiling questions."""

    BOOLEAN = "boolean"
    CURRENCY = "currency"
    INTEGER = "integer"
    TEXT = "text"
    ENUM = "enum"
    CONSENT = "consent"
    CONFIRMATION = "confirmation"


class DocumentType(StrEnum):
    """Supported identity document types for the demo."""

    CC = "CC"
    CE = "CE"
    PPT = "PPT"
    OTRO = "OTRO"


class IdentityStatus(StrEnum):
    """Identity resolution status for a lead."""

    NOT_CHECKED = "not_checked"
    KNOWN_AFFILIATE = "known_affiliate"
    KNOWN_NON_AFFILIATE = "known_non_affiliate"
    NEW_LEAD = "new_lead"
    POSSIBLE_MATCH = "possible_match"
    IDENTITY_NOT_VERIFIED = "identity_not_verified"


class DataSource(StrEnum):
    """Allowed provenance sources for lead fields."""

    MOCK_AFFILIATION_SERVICE = "mock_affiliation_service"
    OFFICIAL_SYSTEM = "official_system"
    EMPLOYER_REPORT = "employer_report"
    CRM = "crm"
    HISTORICAL_DATA = "historical_data"
    USER_DECLARED = "user_declared"
    INFERRED = "inferred"


class FieldProvenance(BaseModel):
    """Traceability metadata for a single lead field."""

    source: DataSource
    confirmed: bool = False
    requires_confirmation: bool = False
    updated_at: datetime | None = None
    previous_value: Any | None = None


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

    # Identity / mock affiliation enrichment (optional, backward compatible).
    document_type: DocumentType | None = None
    document_number: str | None = None
    known_lead: bool = False
    identity_status: IdentityStatus = IdentityStatus.NOT_CHECKED
    identity_verified: bool = False
    profile_source: DataSource | None = None
    prefilled_fields: list[str] = Field(default_factory=list)
    fields_to_confirm: list[str] = Field(default_factory=list)
    identity_lookup_at: datetime | None = None
    data_consent: bool | None = None
    data_consent_at: datetime | None = None
    field_metadata: dict[str, FieldProvenance] = Field(default_factory=dict)
    demo_mode: bool = False
    engagement_label: EngagementLabel | None = None
    engagement_score: int | None = Field(default=None, ge=0, le=100)
    engagement_reason: str | None = None
    engagement_updated_at: datetime | None = None

    # Commercial housing affinity (top recommended project compatibility).
    affinity_percent: float | None = Field(default=None, ge=0, le=100)
    affinity_band: AffinityBand | None = None
    top_project_id: str | None = None
    top_project_name: str | None = None

    @field_validator("correo", mode="before")
    @classmethod
    def coerce_correo(cls, value: object) -> str | None:
        """Drop reserved/demo domains (e.g. .local) instead of failing the lead."""
        return sanitize_optional_email(value)

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
        """Merge fields without clearing previously known valid values.

        Empty lists and False values are allowed when explicitly provided.
        None values are ignored except for nested metadata merges.
        """
        updates = {key: value for key, value in data.items() if value is not None}
        if "field_metadata" in data and data["field_metadata"] is not None:
            merged_meta = dict(self.field_metadata)
            incoming = data["field_metadata"]
            if isinstance(incoming, dict):
                for key, value in incoming.items():
                    merged_meta[key] = value
            updates["field_metadata"] = merged_meta
        if not updates:
            return self
        updates["fecha_actualizacion"] = _utcnow()
        # Re-validate so voice/text updates cannot leave the lead in an
        # unserializable state (e.g. free-text enums).
        merged = {**self.model_dump(), **updates}
        return type(self).model_validate(merged)

    def reset_for_fresh_start(self) -> "Lead":
        """Wipe conversation/profile data; keep document identity and lead id."""
        return Lead(
            id=self.id,
            document_type=self.document_type,
            document_number=self.document_number,
            demo_mode=bool(self.demo_mode),
            fecha_creacion=self.fecha_creacion,
            fecha_actualizacion=_utcnow(),
            estado_lead=LeadStatus.NUEVO,
            known_lead=False,
            identity_status=IdentityStatus.NEW_LEAD,
            identity_verified=False,
            data_consent=False,
            data_consent_at=None,
            consentimiento=None,
            prefilled_fields=[],
            fields_to_confirm=[],
            field_metadata={},
            canal_origen=CanalOrigen.DESCONOCIDO,
        )

    def is_field_confirmed(self, field: str) -> bool:
        meta = self.field_metadata.get(field)
        return bool(meta and meta.confirmed)

    def field_requires_confirmation(self, field: str) -> bool:
        return field in self.fields_to_confirm
