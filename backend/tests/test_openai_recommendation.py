"""Tests for OpenAI recommendation mapping/fallback."""

from uuid import uuid4

from app.core.config import Settings
from app.models.lead import Lead
from app.models.project import HistoricalProfile, Project
from app.models.recommendation import RecommendationStatus
from app.providers.openai_recommendation_provider import OpenAIRecommendationProvider
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

    def get_historical_profile(self, project_id: object):
        project = self.get_by_id(project_id)
        return project.perfil_historico if project else None

    def profiles_available(self) -> bool:
        return True


class FakeOpenAIProvider(OpenAIRecommendationProvider):
    def __init__(self, payload: dict) -> None:
        super().__init__(settings=Settings(OPENAI_API_KEY="test", OPENAI_RECOMMENDER_ENABLED=True))
        self._payload = payload

    @property
    def enabled(self) -> bool:
        return True

    def recommend(self, lead, projects, *, limit=3, profile_document=None):
        return self._payload


def test_openai_recommendation_maps_reason_and_spoken(tmp_path) -> None:
    project_id = uuid4()
    project = Project(
        id=project_id,
        nombre="INARI",
        ubicacion="Chía",
        municipio="Chía",
        brochure_url="https://heyzine.com/flip-book/inari.html",
        perfil_historico=HistoricalProfile(total_buyers=40, affiliated_percentage=90),
    )
    lead = Lead(
        nombre="Luis",
        afiliado=True,
        salario_mensual=2_000_000,
        ubicacion_deseada="Chía",
    )
    provider = FakeOpenAIProvider(
        {
            "recommendations": [
                {
                    "project_id": str(project_id),
                    "project_name": "INARI",
                    "rank": 1,
                    "probability": 0.81,
                    "compatibility_score": 81,
                    "reason": "Queda en Chía y se alinea con tu presupuesto.",
                    "pros": ["Ubicación cercana"],
                    "cons": [],
                    "brochure_url": project.brochure_url,
                }
            ],
            "best_project_id": str(project_id),
            "spoken_summary": (
                "Te recomiendo INARI porque queda en Chía. "
                "Brochure: https://heyzine.com/flip-book/inari.html"
            ),
        }
    )
    service = RecommendationService(
        project_repository=FakeProjectRepository([project]),
        settings=Settings(
            PREFER_OPENAI_RECOMMENDATIONS=True,
            OPENAI_API_KEY="test",
            LEAD_PROFILES_PATH=str(tmp_path),
            PROJECT_ALIASES_PATH=str(tmp_path / "missing.json"),
        ),
        openai_provider=provider,
    )
    result = service.recommend_for_lead(lead, limit=3, persist_profile=True)
    assert result.recommendation_status == RecommendationStatus.COMPLETED
    assert result.engine == "openai"
    assert result.spoken_summary and "INARI" in result.spoken_summary
    assert result.recommended_projects[0].reason
    assert result.recommended_projects[0].brochure_url
    assert result.profile_json_path is not None
