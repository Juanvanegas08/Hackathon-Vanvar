"""Explainable project recommendation engine with optional OpenAI ranking."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings, get_settings
from app.core.constants import (
    ECONOMIC_COMPATIBILITY_DISCLAIMER,
    RECOMMENDATION_CONFIDENCE,
    RECOMMENDATION_DISCLAIMER,
    RECOMMENDATION_ESSENTIAL_FIELDS,
    RECOMMENDATION_WEIGHTS,
)
from app.core.exceptions import ConfigurationError, RealtimeServiceError
from app.models.evaluation import ConfidenceLevel
from app.models.lead import Lead
from app.models.project import Project
from app.models.recommendation import (
    MatchedFactor,
    ProjectRecommendation,
    RecommendationResult,
    RecommendationStatus,
    RegulatoryContext,
)
from app.providers.openai_recommendation_provider import OpenAIRecommendationProvider
from app.repositories.project_repository import ProjectRepository
from app.services.profile_persistence_service import ProfilePersistenceService
from app.services.project_canonicalization_service import ProjectCanonicalizationService
from app.services.project_profile_service import ProjectProfileService
from app.utils.normalization import normalize_for_comparison
from app.utils.project_matching import text_overlap_score

logger = logging.getLogger(__name__)


class RecommendationService:
    """Rank projects for a lead using OpenAI when available, else weighted rules."""

    def __init__(
        self,
        project_repository: ProjectRepository | None = None,
        project_profile_service: ProjectProfileService | None = None,
        settings: Settings | None = None,
        weights: dict[str, int] | None = None,
        openai_provider: OpenAIRecommendationProvider | None = None,
        profile_persistence: ProfilePersistenceService | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._profiles = project_profile_service or ProjectProfileService(
            repository=project_repository,
            settings=self._settings,
        )
        self._canonical = ProjectCanonicalizationService(settings=self._settings)
        self._weights = weights or dict(RECOMMENDATION_WEIGHTS)
        self._openai = openai_provider or OpenAIRecommendationProvider(
            settings=self._settings
        )
        self._profile_persistence = profile_persistence or ProfilePersistenceService(
            settings=self._settings
        )

    def recommend_for_lead(
        self,
        lead: Lead,
        *,
        limit: int = 3,
        include_unavailable: bool = False,
        min_score: float | None = None,
        persist_profile: bool = True,
        brochure_only: bool = True,
    ) -> RecommendationResult:
        """Build ranked recommendations for a lead profile."""
        generated_at = datetime.now(UTC)
        missing_fields = self._missing_lead_fields(lead)
        profile_completeness = self._profile_completeness(lead)
        regulatory = self._regulatory_context(lead)
        profile_path: str | None = None
        profile_document: dict[str, Any] | None = None
        if persist_profile:
            try:
                saved = self._profile_persistence.save_lead_profile(lead)
                profile_path = str(saved)
                profile_document = self._profile_persistence.build_document(lead)
            except OSError:
                logger.warning("No se pudo persistir el perfil del lead %s", lead.id)

        if not self._has_minimum_information(lead):
            return RecommendationResult(
                lead_id=lead.id,
                recommendation_status=RecommendationStatus.INSUFFICIENT_INFORMATION,
                evaluated_projects=0,
                recommended_projects=[],
                profile_completeness=profile_completeness,
                overall_confidence=ConfidenceLevel.LOW,
                missing_lead_fields=missing_fields,
                required_fields=list(RECOMMENDATION_ESSENTIAL_FIELDS),
                regulatory_context=regulatory,
                general_warnings=[
                    "No hay información esencial suficiente para generar recomendaciones."
                ],
                disclaimer=RECOMMENDATION_DISCLAIMER,
                generated_at=generated_at,
                spoken_summary=(
                    "Todavía me faltan algunos datos clave de tu perfil "
                    "para recomendarte un proyecto con confianza."
                ),
                engine="none",
                profile_json_path=profile_path,
            )

        catalog_ready = self._profiles.profiles_ready() or bool(
            self._profiles.repository.list_all()
        )
        if not catalog_ready:
            return RecommendationResult(
                lead_id=lead.id,
                recommendation_status=RecommendationStatus.PROFILES_UNAVAILABLE,
                evaluated_projects=0,
                recommended_projects=[],
                profile_completeness=profile_completeness,
                overall_confidence=ConfidenceLevel.LOW,
                missing_lead_fields=missing_fields,
                required_fields=[],
                regulatory_context=regulatory,
                general_warnings=[
                    "El motor de recomendaciones todavía no tiene proyectos "
                    "disponibles en catálogo."
                ],
                disclaimer=RECOMMENDATION_DISCLAIMER,
                generated_at=generated_at,
                spoken_summary=(
                    "Aún no tengo el catálogo de proyectos listo para recomendarte."
                ),
                engine="none",
                profile_json_path=profile_path,
            )

        projects = self._profiles.repository.list_all()
        if not include_unavailable:
            projects = [project for project in projects if project.disponible]
        if brochure_only:
            with_brochure = [project for project in projects if project.brochure_url]
            # Prefer brochure catalog when available; otherwise keep full catalog.
            if with_brochure:
                projects = with_brochure

        if (
            self._settings.prefer_openai_recommendations
            and self._openai.enabled
        ):
            try:
                return self._recommend_with_openai(
                    lead=lead,
                    projects=projects,
                    limit=limit,
                    min_score=min_score,
                    generated_at=generated_at,
                    missing_fields=missing_fields,
                    profile_completeness=profile_completeness,
                    regulatory=regulatory,
                    profile_path=profile_path,
                    profile_document=profile_document,
                )
            except (ConfigurationError, RealtimeServiceError) as exc:
                logger.warning(
                    "OpenAI recommender fallback to deterministic: %s",
                    exc.message,
                )

        return self._recommend_deterministic(
            lead=lead,
            projects=projects,
            limit=limit,
            min_score=min_score,
            generated_at=generated_at,
            missing_fields=missing_fields,
            profile_completeness=profile_completeness,
            regulatory=regulatory,
            profile_path=profile_path,
        )

    def _recommend_with_openai(
        self,
        *,
        lead: Lead,
        projects: list[Project],
        limit: int,
        min_score: float | None,
        generated_at: datetime,
        missing_fields: list[str],
        profile_completeness: int,
        regulatory: RegulatoryContext,
        profile_path: str | None,
        profile_document: dict[str, Any] | None,
    ) -> RecommendationResult:
        raw = self._openai.recommend(
            lead,
            projects,
            limit=limit,
            profile_document=profile_document,
        )
        by_id = {str(project.id): project for project in projects}
        by_name = {
            (normalize_for_comparison(project.nombre) or ""): project
            for project in projects
        }
        recommendations: list[ProjectRecommendation] = []
        for index, item in enumerate(raw.get("recommendations", []), start=1):
            if not isinstance(item, dict):
                continue
            project = by_id.get(str(item.get("project_id") or ""))
            if project is None:
                name_key = normalize_for_comparison(str(item.get("project_name") or ""))
                project = by_name.get(name_key or "")
            if project is None:
                continue

            score = float(item.get("compatibility_score") or 0)
            probability = item.get("probability")
            if probability is None and score:
                probability = round(score / 100.0, 4)
            if min_score is not None and score < min_score:
                continue

            reason = str(item.get("reason") or "").strip() or None
            pros = [str(value) for value in item.get("pros", []) if value]
            cons = [str(value) for value in item.get("cons", []) if value]
            matched: list[MatchedFactor] = []
            if reason:
                matched.append(
                    MatchedFactor(
                        factor="openai_reason",
                        message=reason,
                        contribution=round(min(100.0, max(0.0, score)), 2),
                    )
                )

            canonical_id = str(
                project.metadata.get("canonical_project_id")
                or self._canonical.resolve_canonical_id(project.nombre)[0]
            )
            canonical_name = str(
                project.metadata.get("canonical_name")
                or self._canonical.resolve_canonical_id(project.nombre)[1]
            )
            aliases = [
                str(alias)
                for alias in project.metadata.get("aliases", [project.nombre])
            ]
            recommendations.append(
                ProjectRecommendation(
                    project_id=canonical_id,
                    project_name=canonical_name,
                    canonical_project_id=canonical_id,
                    rank=int(item.get("rank") or index),
                    compatibility_score=round(min(100.0, max(0.0, score)), 2),
                    confidence=ConfidenceLevel.MEDIUM,
                    matched_factors=matched,
                    warnings=[],
                    unavailable_factors=[],
                    brochure_url=project.brochure_url or item.get("brochure_url"),
                    tour_360_url=project.recorrido_360_url,
                    municipio=project.municipio,
                    departamento=project.departamento,
                    etapa=project.etapa,
                    historical_profile_available=project.perfil_historico.total_buyers > 0,
                    aliases=aliases,
                    metadata={
                        "original_names": aliases,
                        "catalog_project_id": str(project.id),
                        "engine": "openai",
                    },
                    reason=reason,
                    probability=(
                        float(probability)
                        if probability is not None
                        else None
                    ),
                    pros=pros,
                    cons=cons,
                )
            )

        recommendations = self._dedupe_canonical(recommendations)
        recommendations.sort(
            key=lambda item: (
                -(item.probability or item.compatibility_score / 100.0),
                item.project_name.lower(),
            )
        )
        top = recommendations[: max(1, min(limit, 10))] if recommendations else []
        for index, item in enumerate(top, start=1):
            item.rank = index

        spoken = str(raw.get("spoken_summary") or "").strip() or None
        if not spoken and top:
            best = top[0]
            spoken = (
                f"Te recomiendo el proyecto {best.project_name}"
                + (f" porque {best.reason}" if best.reason else "")
                + (
                    f". Puedes ver el brochure aquí: {best.brochure_url}."
                    if best.brochure_url
                    else "."
                )
            )

        status = (
            RecommendationStatus.NO_MATCHES
            if not top
            else RecommendationStatus.COMPLETED
        )
        return RecommendationResult(
            lead_id=lead.id,
            recommendation_status=status,
            evaluated_projects=len(projects),
            recommended_projects=top,
            profile_completeness=profile_completeness,
            overall_confidence=(
                ConfidenceLevel.MEDIUM if top else ConfidenceLevel.LOW
            ),
            missing_lead_fields=missing_fields,
            required_fields=[],
            regulatory_context=regulatory,
            general_warnings=[ECONOMIC_COMPATIBILITY_DISCLAIMER],
            disclaimer=RECOMMENDATION_DISCLAIMER,
            generated_at=generated_at,
            spoken_summary=spoken,
            engine="openai",
            profile_json_path=profile_path,
        )

    def _recommend_deterministic(
        self,
        *,
        lead: Lead,
        projects: list[Project],
        limit: int,
        min_score: float | None,
        generated_at: datetime,
        missing_fields: list[str],
        profile_completeness: int,
        regulatory: RegulatoryContext,
        profile_path: str | None,
    ) -> RecommendationResult:
        scored: list[ProjectRecommendation] = []
        general_warnings = [ECONOMIC_COMPATIBILITY_DISCLAIMER]
        for project in projects:
            recommendation = self._score_project(lead, project)
            if min_score is not None and recommendation.compatibility_score < min_score:
                continue
            scored.append(recommendation)

        scored = self._dedupe_canonical(scored)
        scored.sort(
            key=lambda item: (-item.compatibility_score, item.project_name.lower()),
        )
        top = scored[: max(1, min(limit, 10))]
        for index, item in enumerate(top, start=1):
            item.rank = index
            item.probability = round(item.compatibility_score / 100.0, 4)
            if not item.reason and item.matched_factors:
                item.reason = item.matched_factors[0].message

        status = (
            RecommendationStatus.NO_MATCHES
            if not top
            else RecommendationStatus.COMPLETED
        )
        spoken = None
        if top:
            best = top[0]
            spoken = (
                f"Según tu perfil, la mejor opción es {best.project_name}"
                + (f" porque {best.reason}" if best.reason else "")
            )
            if best.brochure_url:
                spoken += f". Aquí tienes el brochure: {best.brochure_url}."
            if len(top) > 1:
                extras = []
                for item in top[1:]:
                    extras.append(
                        f"{item.project_name}"
                        + (f" ({item.reason})" if item.reason else "")
                    )
                spoken += " También te pueden interesar: " + "; ".join(extras) + "."

        return RecommendationResult(
            lead_id=lead.id,
            recommendation_status=status,
            evaluated_projects=len(projects),
            recommended_projects=top,
            profile_completeness=profile_completeness,
            overall_confidence=self._overall_confidence(lead, top),
            missing_lead_fields=missing_fields,
            required_fields=[],
            regulatory_context=regulatory,
            general_warnings=general_warnings,
            disclaimer=RECOMMENDATION_DISCLAIMER,
            generated_at=generated_at,
            spoken_summary=spoken,
            engine="deterministic",
            profile_json_path=profile_path,
        )

    def _score_project(self, lead: Lead, project: Project) -> ProjectRecommendation:
        contributions: dict[str, float] = {}
        matched: list[MatchedFactor] = []
        unavailable: list[str] = []
        warnings: list[str] = []

        location_score = self._score_location(lead, project)
        if location_score is None:
            unavailable.append("ubicacion")
        else:
            contributions["ubicacion"] = location_score
            if location_score > 0:
                matched.append(
                    MatchedFactor(
                        factor="ubicacion",
                        message=(
                            "El proyecto presenta coincidencia con la ubicación "
                            "o zona indicada por el lead."
                        ),
                        contribution=round(
                            location_score * self._weights["ubicacion"],
                            2,
                        ),
                    )
                )

        economic_score, economic_warning = self._score_economic(lead, project)
        if economic_score is None:
            unavailable.append("compatibilidad_economica")
            if economic_warning:
                warnings.append(economic_warning)
        else:
            contributions["compatibilidad_economica"] = economic_score
            if economic_score > 0:
                matched.append(
                    MatchedFactor(
                        factor="salario",
                        message=(
                            "El rango de ingresos coincide con una parte importante "
                            "de los compradores históricos."
                        ),
                        contribution=round(
                            economic_score * self._weights["compatibilidad_economica"],
                            2,
                        ),
                    )
                )
            if economic_warning:
                warnings.append(economic_warning)

        affiliation_score = self._score_affiliation(lead, project)
        if affiliation_score is None:
            unavailable.append("afiliacion")
        else:
            contributions["afiliacion"] = affiliation_score
            if lead.afiliado is True and affiliation_score > 0:
                matched.append(
                    MatchedFactor(
                        factor="afiliacion",
                        message=(
                            "El proyecto presenta participación histórica "
                            "de compradores afiliados."
                        ),
                        contribution=round(
                            affiliation_score * self._weights["afiliacion"],
                            2,
                        ),
                    )
                )
            elif lead.afiliado is False:
                warnings.append(
                    "Lead no afiliado: permanece elegible sujeto a disponibilidad "
                    "comercial dentro de la política 90/10."
                )

        segment_score = self._score_segment(lead, project)
        if segment_score is None:
            unavailable.append("segmento")
        else:
            contributions["segmento"] = segment_score

        household_score = self._score_household(lead, project)
        if household_score is None:
            unavailable.append("composicion_familiar")
        else:
            contributions["composicion_familiar"] = household_score
            if household_score > 0:
                matched.append(
                    MatchedFactor(
                        factor="composicion_familiar",
                        message=(
                            "La composición del hogar es compatible con el perfil "
                            "histórico del proyecto."
                        ),
                        contribution=round(
                            household_score * self._weights["composicion_familiar"],
                            2,
                        ),
                    )
                )

        interest_score = self._score_project_interest(lead, project)
        if interest_score is None:
            unavailable.append("proyecto_interes")
        else:
            contributions["proyecto_interes"] = interest_score
            if interest_score > 0:
                matched.append(
                    MatchedFactor(
                        factor="proyecto_interes",
                        message="Coincide con el proyecto o preferencia declarada.",
                        contribution=round(
                            interest_score * self._weights["proyecto_interes"],
                            2,
                        ),
                    )
                )

        extras_score = self._score_additional_preferences(lead, project)
        if extras_score is None:
            unavailable.append("preferencias_adicionales")
        else:
            contributions["preferencias_adicionales"] = extras_score

        score = self._normalize_score(contributions)
        confidence = self._project_confidence(lead, project, contributions)

        if project.perfil_historico.total_buyers == 0:
            warnings.append(
                "El proyecto no tiene muestra histórica emparejada; "
                "la recomendación se basa en datos de catálogo limitados."
            )
        if not project.perfil_historico.historical_price_reliable:
            warnings.append(
                "No fue posible comparar el valor del proyecto porque el catálogo "
                "no tiene un precio confiable."
            )
        if lead.situacion_crediticia is not None:
            warnings.append(
                "La situación crediticia declarada no excluye proyectos; "
                "puede requerir acompañamiento comercial."
            )

        canonical_id = str(
            project.metadata.get("canonical_project_id")
            or self._canonical.resolve_canonical_id(project.nombre)[0]
        )
        canonical_name = str(
            project.metadata.get("canonical_name")
            or self._canonical.resolve_canonical_id(project.nombre)[1]
        )
        aliases = [
            str(item)
            for item in project.metadata.get("aliases", [project.nombre])
        ]
        # Deduplicate warnings while preserving order.
        unique_warnings = list(dict.fromkeys(warnings))

        return ProjectRecommendation(
            project_id=canonical_id,
            project_name=canonical_name,
            canonical_project_id=canonical_id,
            rank=0,
            compatibility_score=score,
            confidence=confidence,
            matched_factors=matched,
            warnings=unique_warnings,
            unavailable_factors=unavailable,
            brochure_url=project.brochure_url,
            tour_360_url=project.recorrido_360_url,
            municipio=project.municipio,
            departamento=project.departamento,
            etapa=project.etapa,
            historical_profile_available=project.perfil_historico.total_buyers > 0,
            aliases=aliases,
            metadata={
                "original_names": aliases,
                "catalog_project_id": str(project.id),
            },
        )

    def _dedupe_canonical(
        self,
        recommendations: list[ProjectRecommendation],
    ) -> list[ProjectRecommendation]:
        """Keep the best-scoring recommendation per canonical project."""
        best: dict[str, ProjectRecommendation] = {}
        for item in recommendations:
            current = best.get(item.canonical_project_id)
            if current is None or item.compatibility_score > current.compatibility_score:
                best[item.canonical_project_id] = item
        return list(best.values())

    def _normalize_score(self, contributions: dict[str, float]) -> float:
        if not contributions:
            return 0.0
        numerator = 0.0
        denominator = 0.0
        for factor, ratio in contributions.items():
            weight = float(self._weights[factor])
            numerator += (max(0.0, min(1.0, ratio)) * weight)
            denominator += weight
        if denominator <= 0:
            return 0.0
        return round(min(100.0, max(0.0, (numerator / denominator) * 100)), 2)

    def _score_location(self, lead: Lead, project: Project) -> float | None:
        desired = lead.ubicacion_deseada
        if not desired:
            return None
        aliases = [str(item) for item in project.metadata.get("aliases", [])]
        targets = [
            project.ubicacion,
            project.municipio,
            project.departamento,
            project.nombre,
            *aliases,
            *project.perfil_historico.frequent_locations,
        ]
        usable = [target for target in targets if target]
        if not usable:
            # Still allow name-token matching against project name only.
            usable = [project.nombre]
        best = max(text_overlap_score(desired, target) for target in usable)
        return best

    def _score_economic(
        self,
        lead: Lead,
        project: Project,
    ) -> tuple[float | None, str | None]:
        income = lead.ingreso_hogar if lead.ingreso_hogar is not None else lead.salario_mensual
        if income is None:
            return None, None

        warning = None
        profile = project.perfil_historico
        salary_dist = profile.salary_range_distribution
        if not salary_dist and not self._settings.is_smmlv_configured:
            return None, "No hay distribución salarial histórica ni SMMLV configurado."

        score = 0.0
        if salary_dist and self._settings.is_smmlv_configured:
            band = self._salary_band_label(income)
            # Direct band match plus neighboring band partial credit.
            score = (salary_dist.get(band, 0.0) / 100.0) if band else 0.0
            if score == 0.0:
                # Partial credit if any nearby historical mass exists for similar bands.
                for label, pct in salary_dist.items():
                    if self._bands_compatible(band, label):
                        score = max(score, min(0.7, pct / 100.0))
            if score == 0.0 and salary_dist:
                # Soft fallback: presence of historical salary data with unknown band.
                score = 0.25
        elif salary_dist:
            score = 0.35
            warning = (
                "Compatibilidad salarial aproximada: SMMLV no configurado; "
                "se usó solo la existencia de rangos históricos."
            )
        else:
            score = 0.3
            warning = (
                "Sin distribución salarial histórica suficiente; "
                "aporte económico limitado."
            )

        if lead.ahorro is not None and lead.ahorro > 0:
            score = min(1.0, score + 0.1)

        if profile.historical_price_reliable and profile.historical_price_median is not None:
            # Orientative only; never claim mortgage capacity.
            ratio = income * 12 / profile.historical_price_median
            if ratio >= 0.2:
                score = min(1.0, score + 0.15)
            elif ratio < 0.05:
                score = max(0.0, score - 0.15)
                warning = (
                    (warning + " ") if warning else ""
                ) + "El precio histórico mediano es alto frente al ingreso declarado."
        elif project.valor_minimo is not None or profile.historical_price_median is not None:
            warning = (
                (warning + " ") if warning else ""
            ) + (
                "No fue posible comparar el valor del proyecto porque el catálogo "
                "no tiene un precio confiable."
            )

        return score, warning

    def _score_affiliation(self, lead: Lead, project: Project) -> float | None:
        if lead.afiliado is None:
            return None
        affiliated_pct = project.perfil_historico.affiliated_percentage
        if affiliated_pct is None:
            # Neutral when project has no affiliation history.
            return 0.4 if lead.afiliado else 0.35
        if lead.afiliado:
            return min(1.0, affiliated_pct / 100.0 + 0.15)
        # Non-affiliated leads stay eligible; mild score based on historical openness.
        non_aff = project.perfil_historico.non_affiliated_percentage
        if non_aff is None:
            non_aff = max(0.0, 100.0 - affiliated_pct)
        return min(1.0, max(0.25, non_aff / 100.0))

    def _score_segment(self, lead: Lead, project: Project) -> float | None:
        # Lead model has no commercial segment field; do not invent one from category.
        _ = lead
        if not project.perfil_historico.segments:
            return None
        return None

    def _score_household(self, lead: Lead, project: Project) -> float | None:
        has_lead_household = (
            lead.personas_hogar is not None
            or lead.personas_a_cargo is not None
            or lead.beneficiarios_registrados is not None
        )
        if not has_lead_household:
            return None

        profile = project.perfil_historico
        if not profile.dependents_distribution and not profile.household_composition_distribution:
            return 0.4

        score = 0.4
        dependents = (
            lead.personas_a_cargo
            if lead.personas_a_cargo is not None
            else lead.beneficiarios_registrados
        )
        if dependents is not None and profile.dependents_distribution:
            pct = 0.0
            for candidate in (str(dependents), str(float(dependents)), f"{dependents}.0"):
                pct = max(pct, profile.dependents_distribution.get(candidate, 0.0))
            score = max(score, min(1.0, pct / 100.0 + 0.2))
        if lead.personas_hogar is not None and profile.household_composition_distribution:
            pct = 0.0
            for candidate in (
                str(lead.personas_hogar),
                str(float(lead.personas_hogar)),
                f"{lead.personas_hogar}.0",
            ):
                pct = max(
                    pct,
                    profile.household_composition_distribution.get(candidate, 0.0),
                )
            score = max(score, min(1.0, pct / 100.0 + 0.2))
        return score

    def _score_project_interest(self, lead: Lead, project: Project) -> float | None:
        if not lead.proyecto_interes:
            return None
        return text_overlap_score(lead.proyecto_interes, project.nombre)

    def _score_additional_preferences(self, lead: Lead, project: Project) -> float | None:
        if not lead.empresa and lead.plazo_compra is None:
            return None
        score = 0.3
        if lead.empresa and project.perfil_historico.frequent_companies:
            company = normalize_for_comparison(lead.empresa)
            for item in project.perfil_historico.frequent_companies:
                if company and company in (normalize_for_comparison(item) or ""):
                    score = 1.0
                    break
        if lead.plazo_compra is not None:
            score = max(score, 0.5)
        return score

    def _salary_band_label(self, income: float) -> str | None:
        if not self._settings.is_smmlv_configured:
            return None
        smmlv = self._settings.smmlv
        ratio = income / smmlv
        # Labels aligned with observed historical bands in buyers_clean.
        if ratio < 1:
            return "Menor al SMLV"
        if ratio <= 1.5:
            return "Entre 1 y 1.5 SMLV"
        if ratio <= 2:
            return "Entre 1.5 y 2 SMLV"
        if ratio <= 2.5:
            return "Entre 2 y 2.5 SMLV"
        if ratio <= 3:
            return "Entre 2.5 y 3 SMLV"
        if ratio <= 4:
            return "Entre 3 y 4 SMLV"
        return "Mayor a 4 SMLV"

    @staticmethod
    def _bands_compatible(left: str | None, right: str) -> bool:
        if left is None:
            return False
        left_n = normalize_for_comparison(left) or ""
        right_n = normalize_for_comparison(right) or ""
        if left_n == right_n:
            return True
        # Neighboring low bands.
        low = {"menor al smlv", "entre 1 y 1.5 smlv", "entre 1.5 y 2 smlv"}
        mid = {"entre 2 y 2.5 smlv", "entre 2.5 y 3 smlv", "entre 3 y 4 smlv"}
        high = {"mayor a 4 smlv"}
        return any(left_n in group and right_n in group for group in (low, mid, high))

    def _project_confidence(
        self,
        lead: Lead,
        project: Project,
        contributions: dict[str, float],
    ) -> ConfidenceLevel:
        sample = project.perfil_historico.total_buyers
        criteria = len(contributions)
        lead_fields = 7 - len(self._missing_lead_fields(lead))
        high_sample = int(RECOMMENDATION_CONFIDENCE["min_historical_sample_for_high"])
        med_sample = int(RECOMMENDATION_CONFIDENCE["min_historical_sample_for_medium"])
        high_criteria = int(RECOMMENDATION_CONFIDENCE["min_criteria_for_high"])
        med_criteria = int(RECOMMENDATION_CONFIDENCE["min_criteria_for_medium"])
        high_lead = int(RECOMMENDATION_CONFIDENCE["min_lead_fields_for_high"])

        if sample < med_sample:
            return ConfidenceLevel.LOW
        if (
            sample >= high_sample
            and criteria >= high_criteria
            and lead_fields >= high_lead
        ):
            return ConfidenceLevel.HIGH
        if sample >= med_sample and criteria >= med_criteria:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

    def _overall_confidence(
        self,
        lead: Lead,
        recommendations: list[ProjectRecommendation],
    ) -> ConfidenceLevel:
        if not recommendations:
            return ConfidenceLevel.LOW
        order = {
            ConfidenceLevel.LOW: 0,
            ConfidenceLevel.MEDIUM: 1,
            ConfidenceLevel.HIGH: 2,
        }
        worst = min(recommendations, key=lambda item: order[item.confidence])
        # Incomplete lead cannot be high overall.
        if (
            len(self._missing_lead_fields(lead)) >= 3
            and worst.confidence == ConfidenceLevel.HIGH
        ):
            return ConfidenceLevel.MEDIUM
        return worst.confidence

    def _has_minimum_information(self, lead: Lead) -> bool:
        return any(
            (
                lead.afiliado is not None,
                lead.salario_mensual is not None,
                bool(lead.ubicacion_deseada),
                bool(lead.proyecto_interes),
            )
        )

    def _missing_lead_fields(self, lead: Lead) -> list[str]:
        missing: list[str] = []
        checks = {
            "afiliado": lead.afiliado is None,
            "salario_mensual": lead.salario_mensual is None,
            "ingreso_hogar": lead.ingreso_hogar is None,
            "ahorro": lead.ahorro is None,
            "ubicacion_deseada": not bool(lead.ubicacion_deseada),
            "personas_hogar": lead.personas_hogar is None,
            "proyecto_interes": not bool(lead.proyecto_interes),
            "situacion_crediticia": lead.situacion_crediticia is None,
        }
        for field, is_missing in checks.items():
            if is_missing:
                missing.append(field)
        return missing

    def _profile_completeness(self, lead: Lead) -> int:
        tracked = [
            lead.afiliado is not None,
            lead.salario_mensual is not None,
            lead.ingreso_hogar is not None,
            lead.ahorro is not None,
            bool(lead.ubicacion_deseada),
            lead.personas_hogar is not None or lead.personas_a_cargo is not None,
            bool(lead.proyecto_interes),
            lead.plazo_compra is not None,
        ]
        return int(round(100 * sum(1 for item in tracked if item) / len(tracked)))

    def _regulatory_context(self, lead: Lead) -> RegulatoryContext:
        if lead.afiliado is True:
            return RegulatoryContext(
                affiliation_status="affiliated",
                affiliated=True,
                requires_quota_validation=False,
                message="Lead afiliado: factor favorable para el objetivo regulatorio 90/10.",
            )
        if lead.afiliado is False:
            return RegulatoryContext(
                affiliation_status="non_affiliated",
                affiliated=False,
                requires_quota_validation=True,
                message=(
                    "La recomendación está sujeta a la disponibilidad comercial "
                    "para compradores no afiliados."
                ),
            )
        return RegulatoryContext(
            affiliation_status="unknown",
            affiliated=None,
            requires_quota_validation=True,
            message="Afiliación desconocida: se requiere confirmación antes de priorizar cupo.",
        )
