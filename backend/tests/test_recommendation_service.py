"""Tests for the explainable recommendation engine."""

import inspect
from uuid import uuid4

from app.core.config import Settings
from app.models.lead import Lead
from app.models.project import HistoricalProfile, Project
from app.models.recommendation import RecommendationStatus
from app.services.recommendation_service import RecommendationService


class FakeProjectRepository:
    def __init__(self, projects: list[Project]) -> None:
        self._projects = projects

    def list_all(self) -> list[Project]:
        return list(self._projects)

    def get_by_id(self, project_id: object) -> Project | None:
        for project in self._projects:
            if project.id == project_id:
                return project
        return None

    def get_by_name(self, name: str) -> Project | None:
        return None

    def list_available(self) -> list[Project]:
        return [project for project in self._projects if project.disponible]

    def get_historical_profile(self, project_id: object) -> HistoricalProfile | None:
        project = self.get_by_id(project_id)
        return project.perfil_historico if project else None

    def profiles_available(self) -> bool:
        return True


def _project(
    name: str,
    *,
    disponible: bool = True,
    ubicacion: str | None = None,
    municipio: str | None = None,
    buyers: int = 40,
    affiliated: float = 90.0,
    salary_band: str = "Entre 1 y 1.5 SMLV",
    salary_pct: float = 70.0,
) -> Project:
    return Project(
        id=uuid4(),
        nombre=name,
        ubicacion=ubicacion,
        municipio=municipio,
        disponible=disponible,
        perfil_historico=HistoricalProfile(
            total_buyers=buyers,
            affiliated_percentage=affiliated,
            non_affiliated_percentage=round(100 - affiliated, 2),
            salary_range_distribution={salary_band: salary_pct},
            segments={"Básico": 60.0},
            dependents_distribution={"1.0": 50.0},
            household_composition_distribution={"3.0": 40.0},
            historical_price_reliable=False,
        ),
    )


def _service(projects: list[Project], tmp_aliases: str | None = None) -> RecommendationService:
    repo = FakeProjectRepository(projects)
    settings = Settings(
        SMMLV=1_000_000,
        PROJECT_ALIASES_PATH=tmp_aliases or "./data/processed/missing_aliases.json",
    )
    return RecommendationService(
        project_repository=repo,
        settings=settings,
    )


def test_location_compatible_project_scores_higher() -> None:
    near = _project("Agrupación Monguí", ubicacion="Monguí", municipio="Monguí")
    far = _project("Proyecto Costa", ubicacion="Cartagena", municipio="Cartagena")
    service = _service([near, far])
    lead = Lead(
        afiliado=True,
        salario_mensual=1_200_000,
        ubicacion_deseada="Monguí",
    )
    result = service.recommend_for_lead(lead, limit=2)
    assert result.recommendation_status == RecommendationStatus.COMPLETED
    assert result.recommended_projects[0].canonical_project_id in {
        "agrupacion_mongui",
        "mongui",
        "agrupacion_de_vivienda_mongui",
    } or "mongui" in result.recommended_projects[0].project_name.lower()
    assert (
        result.recommended_projects[0].compatibility_score
        >= result.recommended_projects[1].compatibility_score
    )


def test_salary_compatible_contributes_positively() -> None:
    project = _project("INARI", salary_band="Entre 1 y 1.5 SMLV", salary_pct=80.0)
    service = _service([project])
    lead = Lead(afiliado=True, salario_mensual=1_200_000, ubicacion_deseada="Bogotá")
    result = service.recommend_for_lead(lead, limit=1)
    item = result.recommended_projects[0]
    assert any(factor.factor == "salario" for factor in item.matched_factors)
    assert 0 <= item.compatibility_score <= 100


def test_non_affiliated_is_not_discarded() -> None:
    project = _project("La Arboleda", affiliated=70.0)
    service = _service([project])
    lead = Lead(afiliado=False, salario_mensual=2_000_000, ubicacion_deseada="Arboleda")
    result = service.recommend_for_lead(lead, limit=1)
    assert result.recommendation_status == RecommendationStatus.COMPLETED
    assert len(result.recommended_projects) == 1
    assert result.regulatory_context is not None
    assert result.regulatory_context.requires_quota_validation is True


def test_unavailable_project_hidden_by_default() -> None:
    available = _project("Disponible", ubicacion="Norte")
    unavailable = _project("Cerrado", ubicacion="Norte", disponible=False)
    service = _service([available, unavailable])
    lead = Lead(afiliado=True, ubicacion_deseada="Norte")
    result = service.recommend_for_lead(lead, limit=5)
    names = {item.project_name for item in result.recommended_projects}
    assert "Cerrado" not in names
    assert "Disponible" in names


def test_missing_fields_reduce_confidence_and_exclude_criterion() -> None:
    project = _project("ABETO", buyers=50)
    service = _service([project])
    lead = Lead(ubicacion_deseada="ABETO")  # no salary / affiliation
    result = service.recommend_for_lead(lead, limit=1)
    item = result.recommended_projects[0]
    assert "compatibilidad_economica" in item.unavailable_factors
    assert "afiliacion" in item.unavailable_factors
    assert item.confidence.value in {"low", "medium"}
    assert result.disclaimer


def test_score_always_between_0_and_100_and_deterministic() -> None:
    projects = [
        _project("A", ubicacion="Zona A"),
        _project("B", ubicacion="Zona B"),
    ]
    service = _service(projects)
    lead = Lead(
        afiliado=True,
        salario_mensual=1_300_000,
        ubicacion_deseada="Zona A",
        personas_hogar=3,
        personas_a_cargo=1,
        proyecto_interes="A",
    )
    first = service.recommend_for_lead(lead, limit=2)
    second = service.recommend_for_lead(lead, limit=2)
    assert first.model_dump(exclude={"generated_at"}) == second.model_dump(
        exclude={"generated_at"}
    )
    for item in first.recommended_projects:
        assert 0 <= item.compatibility_score <= 100
        assert item.matched_factors or item.unavailable_factors


def test_gender_age_stratum_not_in_scoring_logic() -> None:
    source = inspect.getsource(RecommendationService)
    for token in (r"\bgenero\b", r"\bedad\b", r"\bestrato\b", r"\bgender\b", r"\bage\b"):
        import re

        assert re.search(token, source.lower()) is None


def test_insufficient_information_status() -> None:
    service = _service([_project("X")])
    result = service.recommend_for_lead(Lead(), limit=3)
    assert result.recommendation_status == RecommendationStatus.INSUFFICIENT_INFORMATION
    assert result.recommended_projects == []
    assert "afiliado" in result.required_fields
