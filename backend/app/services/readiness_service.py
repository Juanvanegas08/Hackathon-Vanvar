"""Preliminary purchase-readiness / profile-completeness scoring."""

from app.core.constants import (
    CRITICAL_READINESS_FIELDS,
    READINESS_DISCLAIMER,
    READINESS_WEIGHTS,
)
from app.models.evaluation import ConfidenceLevel, ReadinessResult
from app.models.lead import Lead, LeadStatus
from app.services.question_service import QuestionService


class ReadinessService:
    """Compute an explainable readiness score (not a credit approval)."""

    def __init__(self, question_service: QuestionService | None = None) -> None:
        self._questions = question_service or QuestionService()

    def evaluate(self, lead: Lead) -> ReadinessResult:
        """Evaluate profile readiness and recommend a lead status."""
        score_parts = self._score_parts(lead)
        score = min(100, sum(score_parts.values()))
        complete_fields = self._questions.list_complete_fields(lead)
        missing_fields = self._questions.list_missing_fields(lead)
        positive_factors = self._positive_factors(lead, score_parts)
        gaps = self._gaps(lead, missing_fields)
        warnings = self._warnings(lead)
        confidence = self._confidence(lead, missing_fields)
        status = self._resolve_status(lead, score, gaps, warnings)
        next_action = self._next_action(status, gaps, missing_fields)

        return ReadinessResult(
            lead_id=lead.id,
            readiness_score=score,
            confidence=confidence,
            status=status,
            complete_fields=complete_fields,
            missing_fields=missing_fields,
            positive_factors=positive_factors,
            gaps=gaps,
            next_action=next_action,
            warnings=warnings,
            disclaimer=READINESS_DISCLAIMER,
        )

    def _score_parts(self, lead: Lead) -> dict[str, int]:
        composition_known = (
            lead.personas_hogar is not None
            or lead.personas_a_cargo is not None
            or lead.beneficiarios_registrados is not None
        )
        checks: dict[str, bool] = {
            "affiliation_identified": lead.afiliado is not None,
            "personal_income_known": lead.salario_mensual is not None,
            "household_income_known": lead.ingreso_hogar is not None,
            "savings_known": lead.ahorro is not None,
            "obligations_known": lead.obligaciones_mensuales is not None,
            "housing_status_known": lead.tiene_vivienda is not None,
            "credit_situation_known": lead.situacion_crediticia is not None,
            "desired_location_known": bool(lead.ubicacion_deseada),
            "purchase_timeline_known": lead.plazo_compra is not None,
            "household_composition_known": composition_known,
        }
        return {
            key: READINESS_WEIGHTS[key] if present else 0
            for key, present in checks.items()
        }

    def _positive_factors(self, lead: Lead, score_parts: dict[str, int]) -> list[str]:
        labels = {
            "affiliation_identified": "Afiliación identificada",
            "personal_income_known": "Ingreso personal conocido",
            "household_income_known": "Ingreso del hogar conocido",
            "savings_known": "Cuenta con ahorro registrado",
            "obligations_known": "Obligaciones financieras conocidas",
            "housing_status_known": "Estado de vivienda conocido",
            "credit_situation_known": "Situación crediticia declarada",
            "desired_location_known": "Ubicación deseada conocida",
            "purchase_timeline_known": "Plazo de compra conocido",
            "household_composition_known": "Composición del hogar conocida",
        }
        factors = [labels[key] for key, points in score_parts.items() if points > 0]
        if lead.afiliado is False:
            factors.append("Lead no afiliado en evaluación (no descartado)")
        if lead.ahorro is not None and lead.ahorro > 0:
            factors.append("Cuenta con ahorro")
        return factors

    def _gaps(self, lead: Lead, missing_fields: list[str]) -> list[str]:
        gap_messages = {
            "consentimiento": "Falta el consentimiento para continuar",
            "afiliado": "Falta identificar la afiliación a Colsubsidio",
            "salario_mensual": "Falta el salario mensual personal",
            "ingreso_hogar": "Falta el ingreso total del hogar",
            "ahorro": "Falta el ahorro disponible",
            "obligaciones_mensuales": "Faltan las obligaciones financieras mensuales",
            "tiene_vivienda": "Falta el estado de vivienda actual",
            "personas_hogar": "Falta la composición del hogar",
            "personas_a_cargo": "Faltan las personas a cargo o beneficiarios",
            "situacion_crediticia": "Falta confirmar la situación crediticia",
            "ubicacion_deseada": "Falta la ubicación deseada",
            "plazo_compra": "Falta el plazo estimado de compra",
        }
        gaps = [gap_messages[field] for field in missing_fields if field in gap_messages]
        if (
            lead.salario_mensual is not None
            and lead.ingreso_hogar is not None
            and lead.ingreso_hogar < lead.salario_mensual
        ):
            gaps.append(
                "El ingreso del hogar es menor que el ingreso personal (dato contradictorio)"
            )
        return gaps

    def _warnings(self, lead: Lead) -> list[str]:
        warnings: list[str] = []
        if lead.afiliado is False:
            warnings.append(
                "Persona no afiliada: permanece en evaluación según la política 90/10 futura"
            )
        if not lead.afiliacion_confirmada and lead.afiliado is not None:
            warnings.append("La afiliación aún no está confirmada por un sistema oficial")
        if lead.fields_to_confirm:
            warnings.append(
                "Existen datos precargados pendientes de confirmación por el lead"
            )
        if lead.known_lead and not lead.identity_verified:
            warnings.append(
                "Identidad no verificada: la coincidencia proviene de una simulación "
                "y no de autenticación OTP u oficial"
            )
        if lead.demo_mode:
            warnings.append(
                "Modo demostración: los perfiles de afiliación son completamente ficticios"
            )
        if (
            lead.salario_mensual is not None
            and lead.ingreso_hogar is not None
            and lead.ingreso_hogar < lead.salario_mensual
        ):
            warnings.append("Inconsistencia entre ingreso personal e ingreso del hogar")
        return warnings

    def _confidence(self, lead: Lead, missing_fields: list[str]) -> ConfidenceLevel:
        critical_missing = [field for field in CRITICAL_READINESS_FIELDS if field in missing_fields]
        if critical_missing:
            return ConfidenceLevel.LOW
        if lead.fields_to_confirm or (lead.known_lead and not lead.identity_verified):
            return ConfidenceLevel.MEDIUM
        if missing_fields or not lead.afiliacion_confirmada:
            return ConfidenceLevel.MEDIUM
        # Inferred sources cannot reach high confidence.
        inferred = any(
            meta.source.value == "inferred" for meta in lead.field_metadata.values()
        )
        if inferred:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.HIGH

    def _resolve_status(
        self,
        lead: Lead,
        score: int,
        gaps: list[str],
        warnings: list[str],
    ) -> LeadStatus:
        contradictory = any("contradictorio" in gap.lower() for gap in gaps) or any(
            "Inconsistencia" in warning for warning in warnings
        )
        if contradictory:
            return LeadStatus.REQUIERE_REVISION

        critical_gaps = {
            "Falta identificar la afiliación a Colsubsidio",
            "Falta el salario mensual personal",
            "Falta el ahorro disponible",
        }
        has_critical_gaps = any(gap in critical_gaps for gap in gaps)

        if lead.afiliado is False and score >= 45:
            return LeadStatus.NO_AFILIADO_EN_EVALUACION

        if score >= 75 and not has_critical_gaps:
            return LeadStatus.LISTO_PARA_ASESOR
        if score >= 45:
            return LeadStatus.PERFIL_INCOMPLETO
        return LeadStatus.RUTA_NUTRICION

    def _next_action(
        self,
        status: LeadStatus,
        gaps: list[str],
        missing_fields: list[str],
    ) -> str:
        if status == LeadStatus.REQUIERE_REVISION:
            return "Revisar inconsistencias de ingresos antes de contactar al asesor"
        if status == LeadStatus.NO_AFILIADO_EN_EVALUACION:
            return (
                "Mantener en evaluación no afiliado y completar datos pendientes "
                "sin descartar el lead"
            )
        if status == LeadStatus.LISTO_PARA_ASESOR:
            if gaps:
                return "Completar datos menores pendientes y preparar contacto comercial"
            return "Validar información pendiente y agendar conversación comercial"
        if missing_fields:
            first = missing_fields[0]
            return f"Completar el campo prioritario: {first}"
        return "Continuar nutrición del lead con información faltante"
