"""Map between domain Lead and PostgreSQL lead/identity rows."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.models.lead import (
    AffiliationCategory,
    CanalOrigen,
    CreditSituation,
    DataSource,
    DocumentType,
    EngagementLabel,
    FieldProvenance,
    IdentityStatus,
    Lead,
    LeadStatus,
    PurchaseTimeline,
)
from app.utils.commercial_affinity import AffinityBand, parse_commercial_snapshot
from app.utils.profile_progress import compute_profile_progress

DOMAIN_TO_DB_STATUS: dict[str, str] = {
    LeadStatus.NUEVO.value: "new",
    LeadStatus.PERFIL_INCOMPLETO.value: "profile_incomplete",
    LeadStatus.LISTO_PARA_ASESOR.value: "ready_for_advisor",
    LeadStatus.RUTA_NUTRICION.value: "nutrition_route",
    LeadStatus.NO_AFILIADO_EN_EVALUACION.value: "non_affiliate_under_review",
    LeadStatus.REQUIERE_REVISION.value: "requires_review",
}

DB_TO_DOMAIN_STATUS: dict[str, LeadStatus] = {
    value: LeadStatus(key) for key, value in DOMAIN_TO_DB_STATUS.items()
}
DB_TO_DOMAIN_STATUS["closed"] = LeadStatus.REQUIERE_REVISION


def domain_status_to_db(status: LeadStatus | str) -> str:
    value = status.value if isinstance(status, LeadStatus) else str(status)
    return DOMAIN_TO_DB_STATUS.get(value, "new")


def db_status_to_domain(status: str | None) -> LeadStatus:
    if not status:
        return LeadStatus.NUEVO
    return DB_TO_DOMAIN_STATUS.get(status, LeadStatus.NUEVO)


def split_display_name(nombre: str | None) -> tuple[str | None, str | None, str | None]:
    if not nombre or not nombre.strip():
        return None, None, None
    parts = nombre.strip().split()
    if len(parts) == 1:
        return parts[0], None, parts[0]
    return parts[0], " ".join(parts[1:]), nombre.strip()


def money(value: float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(round(float(value), 2)))


def money_to_float(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def enum_or_none(enum_cls: type[Any], value: object) -> Any:
    if value is None:
        return None
    try:
        return enum_cls(value)
    except (TypeError, ValueError):
        return None


def build_profile_columns(lead: Lead, document: dict[str, Any]) -> dict[str, Any]:
    beneficiaries = lead.beneficiarios_registrados
    return {
        "affiliated": lead.afiliado,
        "affiliation_category": (
            lead.categoria_afiliacion.value
            if lead.categoria_afiliacion is not None
            else None
        ),
        "company_name": lead.empresa,
        "personal_income": money(lead.salario_mensual),
        "household_income": money(lead.ingreso_hogar),
        "savings": money(lead.ahorro),
        "monthly_obligations": money(lead.obligaciones_mensuales),
        "has_home": lead.tiene_vivienda,
        "household_size": lead.personas_hogar,
        "dependents": lead.personas_a_cargo,
        "beneficiaries_registered": (
            None if beneficiaries is None else bool(beneficiaries > 0)
        ),
        "credit_situation": (
            lead.situacion_crediticia.value
            if lead.situacion_crediticia is not None
            else None
        ),
        "current_location": lead.ubicacion_actual,
        "desired_location": lead.ubicacion_deseada,
        "purchase_horizon": (
            lead.plazo_compra.value if lead.plazo_compra is not None else None
        ),
        "project_interest": lead.proyecto_interes,
        "profile_completeness": compute_profile_progress(lead),
        "additional_preferences": {
            "beneficiarios_registrados": beneficiaries,
            "afiliacion_confirmada": lead.afiliacion_confirmada,
            "canal_origen": (
                lead.canal_origen.value
                if hasattr(lead.canal_origen, "value")
                else str(lead.canal_origen)
            ),
            "prefilled_fields": list(lead.prefilled_fields),
            "fields_to_confirm": list(lead.fields_to_confirm),
            "demo_mode": lead.demo_mode,
            "engagement": {
                "label": (
                    lead.engagement_label.value
                    if lead.engagement_label is not None
                    else None
                ),
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
                "affinity_band": (
                    lead.affinity_band.value if lead.affinity_band is not None else None
                ),
                "top_project_id": lead.top_project_id,
                "top_project_name": lead.top_project_name,
            },
        },
        "profile_document": document,
    }


def domain_lead_from_rows(
    *,
    lead_id: UUID,
    person_display_name: str | None,
    lead_known: bool,
    lead_identity_status: str,
    lead_status: str,
    profile: Any | None,
    document_type: str | None,
    document_number: str | None,
    phone: str | None = None,
    email: str | None = None,
) -> Lead:
    extras = getattr(profile, "additional_preferences", None) or {}
    document = getattr(profile, "profile_document", None) or {}
    if not isinstance(document, dict) or not document:
        nested = extras.get("profile_document") if isinstance(extras, dict) else None
        document = nested if isinstance(nested, dict) else {}
    identity = document.get("identity", {}) if isinstance(document, dict) else {}
    contact = document.get("contact", {}) if isinstance(document, dict) else {}
    financial = document.get("financial", {}) if isinstance(document, dict) else {}
    household = document.get("household", {}) if isinstance(document, dict) else {}
    credit = document.get("credit", {}) if isinstance(document, dict) else {}
    prefs = document.get("housing_preferences", {}) if isinstance(document, dict) else {}
    affiliation = document.get("affiliation", {}) if isinstance(document, dict) else {}
    consent = document.get("consent", {}) if isinstance(document, dict) else {}
    provenance = document.get("field_provenance", {}) if isinstance(document, dict) else {}

    beneficiaries = household.get("beneficiarios_registrados")
    if beneficiaries is None:
        beneficiaries = extras.get("beneficiarios_registrados")

    field_metadata: dict[str, FieldProvenance] = {}
    if isinstance(provenance, dict):
        for field, meta in provenance.items():
            if not isinstance(meta, dict):
                continue
            source = enum_or_none(DataSource, meta.get("source")) or DataSource.USER_DECLARED
            updated_at = meta.get("updated_at")
            field_metadata[field] = FieldProvenance(
                source=source,
                confirmed=bool(meta.get("confirmed")),
                requires_confirmation=bool(meta.get("requires_confirmation")),
                updated_at=(
                    datetime.fromisoformat(updated_at)
                    if isinstance(updated_at, str)
                    else None
                ),
            )

    engagement = extras.get("engagement") if isinstance(extras.get("engagement"), dict) else {}
    raw_score = engagement.get("score", extras.get("engagement_score"))
    engagement_score = int(raw_score) if isinstance(raw_score, (int, float)) else None
    engagement_updated_raw = engagement.get("updated_at")

    commercial_raw = None
    if isinstance(document, dict) and isinstance(document.get("commercial"), dict):
        commercial_raw = document.get("commercial")
    elif isinstance(extras.get("commercial"), dict):
        commercial_raw = extras.get("commercial")
    commercial = parse_commercial_snapshot(commercial_raw) or {}

    return Lead(
        id=lead_id,
        nombre=contact.get("nombre") or person_display_name,
        telefono=contact.get("telefono") or phone,
        correo=contact.get("correo") or email,
        canal_origen=enum_or_none(CanalOrigen, contact.get("canal_origen") or extras.get("canal_origen"))
        or CanalOrigen.DESCONOCIDO,
        consentimiento=consent.get("consentimiento"),
        afiliado=(
            affiliation.get("afiliado")
            if affiliation.get("afiliado") is not None
            else getattr(profile, "affiliated", None)
        ),
        afiliacion_confirmada=bool(
            affiliation.get("afiliacion_confirmada", extras.get("afiliacion_confirmada", False))
        ),
        categoria_afiliacion=enum_or_none(
            AffiliationCategory,
            affiliation.get("categoria_afiliacion")
            or getattr(profile, "affiliation_category", None),
        ),
        empresa=affiliation.get("empresa") or getattr(profile, "company_name", None),
        salario_mensual=financial.get("salario_mensual")
        if financial.get("salario_mensual") is not None
        else money_to_float(getattr(profile, "personal_income", None)),
        ingreso_hogar=financial.get("ingreso_hogar")
        if financial.get("ingreso_hogar") is not None
        else money_to_float(getattr(profile, "household_income", None)),
        ahorro=financial.get("ahorro")
        if financial.get("ahorro") is not None
        else money_to_float(getattr(profile, "savings", None)),
        obligaciones_mensuales=financial.get("obligaciones_mensuales")
        if financial.get("obligaciones_mensuales") is not None
        else money_to_float(getattr(profile, "monthly_obligations", None)),
        tiene_vivienda=household.get("tiene_vivienda")
        if household.get("tiene_vivienda") is not None
        else getattr(profile, "has_home", None),
        personas_hogar=household.get("personas_hogar")
        if household.get("personas_hogar") is not None
        else getattr(profile, "household_size", None),
        personas_a_cargo=household.get("personas_a_cargo")
        if household.get("personas_a_cargo") is not None
        else getattr(profile, "dependents", None),
        beneficiarios_registrados=(
            int(beneficiaries) if beneficiaries is not None else None
        ),
        situacion_crediticia=enum_or_none(
            CreditSituation,
            credit.get("situacion_crediticia")
            or getattr(profile, "credit_situation", None),
        ),
        ubicacion_actual=prefs.get("ubicacion_actual")
        or getattr(profile, "current_location", None),
        ubicacion_deseada=prefs.get("ubicacion_deseada")
        or getattr(profile, "desired_location", None),
        plazo_compra=enum_or_none(
            PurchaseTimeline,
            prefs.get("plazo_compra") or getattr(profile, "purchase_horizon", None),
        ),
        proyecto_interes=prefs.get("proyecto_interes")
        or getattr(profile, "project_interest", None),
        estado_lead=db_status_to_domain(lead_status),
        document_type=enum_or_none(
            DocumentType,
            identity.get("document_type") or document_type,
        ),
        document_number=identity.get("document_number") or document_number,
        known_lead=bool(identity.get("known_lead", lead_known)),
        identity_status=enum_or_none(
            IdentityStatus,
            identity.get("identity_status") or lead_identity_status,
        )
        or IdentityStatus.NOT_CHECKED,
        identity_verified=bool(identity.get("identity_verified", False)),
        profile_source=enum_or_none(DataSource, identity.get("profile_source")),
        prefilled_fields=list(
            document.get("prefilled_fields")
            or extras.get("prefilled_fields")
            or []
        ),
        fields_to_confirm=list(
            document.get("fields_to_confirm")
            or extras.get("fields_to_confirm")
            or []
        ),
        data_consent=consent.get("data_consent"),
        data_consent_at=(
            datetime.fromisoformat(consent["data_consent_at"])
            if isinstance(consent.get("data_consent_at"), str)
            else None
        ),
        field_metadata=field_metadata,
        demo_mode=bool(extras.get("demo_mode", False)),
        engagement_label=enum_or_none(
            EngagementLabel,
            engagement.get("label", extras.get("engagement_label")),
        ),
        engagement_score=engagement_score,
        engagement_reason=engagement.get("reason", extras.get("engagement_reason")),
        engagement_updated_at=(
            datetime.fromisoformat(engagement_updated_raw)
            if isinstance(engagement_updated_raw, str)
            else None
        ),
        affinity_percent=(
            float(commercial["affinity_percent"])
            if commercial.get("affinity_percent") is not None
            else None
        ),
        affinity_band=enum_or_none(AffinityBand, commercial.get("affinity_band")),
        top_project_id=commercial.get("top_project_id"),
        top_project_name=commercial.get("top_project_name"),
        fecha_actualizacion=datetime.now(UTC),
    )
