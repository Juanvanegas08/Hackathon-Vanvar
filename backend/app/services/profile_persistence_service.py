"""Build organized lead profile documents for PostgreSQL and LLM prompts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.models.lead import Lead


class ProfilePersistenceService:
    """Serialize leads into a stable nested document (DB / OpenAI payload)."""

    SCHEMA_VERSION = "1.0"

    def __init__(self, settings: object | None = None) -> None:
        # Settings kept for call-site compatibility; profiles are DB-only now.
        self._settings = settings

    def build_document(self, lead: Lead) -> dict[str, Any]:
        """Return an organized profile dictionary ready for persistence."""
        return {
            "schema_version": self.SCHEMA_VERSION,
            "entity": "lead_profile",
            "lead_id": str(lead.id),
            "saved_at": datetime.now(UTC).isoformat(),
            "identity": {
                "document_type": self._enum(lead.document_type),
                "document_number": lead.document_number,
                "known_lead": lead.known_lead,
                "identity_status": self._enum(lead.identity_status),
                "identity_verified": lead.identity_verified,
                "profile_source": self._enum(lead.profile_source),
            },
            "contact": {
                "nombre": lead.nombre,
                "telefono": lead.telefono,
                "correo": str(lead.correo) if lead.correo else None,
                "canal_origen": self._enum(lead.canal_origen),
            },
            "affiliation": {
                "afiliado": lead.afiliado,
                "afiliacion_confirmada": lead.afiliacion_confirmada,
                "categoria_afiliacion": self._enum(lead.categoria_afiliacion),
                "empresa": lead.empresa,
            },
            "financial": {
                "salario_mensual": lead.salario_mensual,
                "ingreso_hogar": lead.ingreso_hogar,
                "ahorro": lead.ahorro,
                "obligaciones_mensuales": lead.obligaciones_mensuales,
            },
            "credit": {
                "situacion_crediticia": self._enum(lead.situacion_crediticia),
            },
            "household": {
                "personas_hogar": lead.personas_hogar,
                "personas_a_cargo": lead.personas_a_cargo,
                "beneficiarios_registrados": lead.beneficiarios_registrados,
                "tiene_vivienda": lead.tiene_vivienda,
            },
            "housing_preferences": {
                "ubicacion_actual": lead.ubicacion_actual,
                "ubicacion_deseada": lead.ubicacion_deseada,
                "plazo_compra": self._enum(lead.plazo_compra),
                "proyecto_interes": lead.proyecto_interes,
            },
            "consent": {
                "consentimiento": lead.consentimiento,
                "data_consent": lead.data_consent,
                "data_consent_at": (
                    lead.data_consent_at.isoformat() if lead.data_consent_at else None
                ),
            },
            "lifecycle": {
                "estado_lead": self._enum(lead.estado_lead),
                "fecha_creacion": lead.fecha_creacion.isoformat(),
                "fecha_actualizacion": lead.fecha_actualizacion.isoformat(),
                "demo_mode": lead.demo_mode,
            },
            "engagement": {
                "label": self._enum(lead.engagement_label),
                "score": lead.engagement_score,
                "reason": lead.engagement_reason,
                "updated_at": (
                    lead.engagement_updated_at.isoformat()
                    if lead.engagement_updated_at
                    else None
                ),
            },
            "commercial": {
                "affinity_percent": lead.affinity_percent,
                "affinity_band": self._enum(lead.affinity_band),
                "top_project_id": lead.top_project_id,
                "top_project_name": lead.top_project_name,
            },
            "field_provenance": {
                field: {
                    "source": self._enum(meta.source),
                    "confirmed": meta.confirmed,
                    "requires_confirmation": meta.requires_confirmation,
                    "updated_at": (
                        meta.updated_at.isoformat() if meta.updated_at else None
                    ),
                }
                for field, meta in lead.field_metadata.items()
            },
            "prefilled_fields": list(lead.prefilled_fields),
            "fields_to_confirm": list(lead.fields_to_confirm),
        }

    @staticmethod
    def _enum(value: object) -> Any:
        if value is None:
            return None
        return getattr(value, "value", value)
