"""Structured advisor summary generation."""

from app.core.constants import READINESS_DISCLAIMER
from app.core.exceptions import InvalidSmmlvError, ValidationBusinessError
from app.models.evaluation import ReadinessResult
from app.models.lead import AffiliationCategory, Lead
from app.models.recommendation import RecommendationStatus
from app.schemas.evaluation import (
    AdvisorSummaryResponse,
    AffiliationSummaryBlock,
    FinancialProfileBlock,
    ReadinessSummaryBlock,
)
from app.services.affiliation_service import AffiliationService
from app.services.readiness_service import ReadinessService
from app.services.recommendation_service import RecommendationService


class SummaryService:
    """Build a structured summary for future commercial advisors."""

    def __init__(
        self,
        readiness_service: ReadinessService | None = None,
        affiliation_service: AffiliationService | None = None,
        recommendation_service: RecommendationService | None = None,
    ) -> None:
        self._readiness = readiness_service or ReadinessService()
        self._affiliation = affiliation_service or AffiliationService()
        self._recommendation = recommendation_service

    def build_summary(
        self,
        lead: Lead,
        readiness: ReadinessResult | None = None,
    ) -> AdvisorSummaryResponse:
        """Create an advisor-facing structured summary."""
        evaluation = readiness or self._readiness.evaluate(lead)
        category: AffiliationCategory | None = lead.categoria_afiliacion
        try:
            affiliation = self._affiliation.calculate_category(
                afiliado=lead.afiliado,
                salario_mensual=lead.salario_mensual,
                afiliacion_confirmada=lead.afiliacion_confirmada,
            )
            category = affiliation.categoria or lead.categoria_afiliacion
        except (InvalidSmmlvError, ValidationBusinessError):
            category = lead.categoria_afiliacion

        fields_to_confirm: list[str] = list(lead.fields_to_confirm)
        if (
            lead.afiliado is not None
            and not lead.afiliacion_confirmada
            and "afiliado" not in fields_to_confirm
        ):
            fields_to_confirm.append("afiliado")

        confirmed_fields = [
            field
            for field, meta in lead.field_metadata.items()
            if meta.confirmed
        ]
        field_sources: dict[str, object] = {
            field: {
                "source": meta.source.value,
                "confirmed": meta.confirmed,
                "requires_confirmation": meta.requires_confirmation,
            }
            for field, meta in lead.field_metadata.items()
        }

        recommended_projects: list[dict[str, object]] = []
        recommendation_warning: str | None = None
        if self._recommendation is None:
            recommendation_warning = (
                "El motor de recomendaciones todavía no tiene perfiles "
                "de proyectos disponibles."
            )
        else:
            result = self._recommendation.recommend_for_lead(lead, limit=3)
            if result.recommendation_status == RecommendationStatus.PROFILES_UNAVAILABLE:
                recommendation_warning = (
                    "El motor de recomendaciones todavía no tiene perfiles "
                    "de proyectos disponibles."
                )
            elif result.recommendation_status == RecommendationStatus.INSUFFICIENT_INFORMATION:
                recommendation_warning = (
                    "Información insuficiente del lead para generar recomendaciones."
                )
            else:
                recommended_projects = [
                    item.model_dump(mode="json") for item in result.recommended_projects
                ]

        identity_context: dict[str, object] = {
            "known_lead": lead.known_lead,
            "identity_status": lead.identity_status.value,
            "identity_verified": lead.identity_verified,
            "profile_source": (
                lead.profile_source.value if lead.profile_source else None
            ),
            "demo_mode": lead.demo_mode,
        }

        return AdvisorSummaryResponse(
            lead_id=lead.id,
            headline=self._headline(lead, evaluation),
            basic_data={
                "nombre": lead.nombre,
                "telefono": lead.telefono,
                "correo": str(lead.correo) if lead.correo else None,
                "canal_origen": (
                    lead.canal_origen.value
                    if hasattr(lead.canal_origen, "value")
                    else str(lead.canal_origen)
                ),
            },
            affiliation=AffiliationSummaryBlock(
                is_affiliated=lead.afiliado,
                category=category,
                confirmed=lead.afiliacion_confirmada,
            ),
            financial_profile=FinancialProfileBlock(
                personal_income=lead.salario_mensual,
                household_income=lead.ingreso_hogar,
                savings=lead.ahorro,
                monthly_obligations=lead.obligaciones_mensuales,
            ),
            household={
                "personas_hogar": lead.personas_hogar,
                "personas_a_cargo": lead.personas_a_cargo,
                "beneficiarios_registrados": lead.beneficiarios_registrados,
                "tiene_vivienda": lead.tiene_vivienda,
            },
            readiness=ReadinessSummaryBlock(
                score=evaluation.readiness_score,
                status=evaluation.status,
                confidence=evaluation.confidence,
            ),
            gaps=evaluation.gaps,
            fields_to_confirm=fields_to_confirm,
            confirmed_fields=confirmed_fields,
            field_sources=field_sources,
            identity_context=identity_context,
            recommended_projects=recommended_projects,
            recommendation_warning=recommendation_warning,
            next_action=evaluation.next_action,
            disclaimer=READINESS_DISCLAIMER,
        )

    @staticmethod
    def _headline(lead: Lead, evaluation: ReadinessResult) -> str:
        if lead.known_lead and lead.afiliado is True:
            return "Lead afiliado conocido con datos precargados"
        if lead.afiliado is True and evaluation.readiness_score >= 75:
            return "Lead afiliado con perfil avanzado"
        if lead.afiliado is True and evaluation.readiness_score >= 45:
            return "Lead afiliado con perfil en construcción"
        if lead.afiliado is False:
            return "Lead no afiliado en evaluación"
        if evaluation.readiness_score < 45:
            return "Lead con perfil inicial para nutrición"
        return "Lead con perfil parcial"
