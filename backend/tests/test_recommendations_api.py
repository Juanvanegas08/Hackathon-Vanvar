"""API tests for recommendations and projects."""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from app.api.deps import (
    get_lead_repository,
    get_lead_service,
    get_project_profile_service,
    get_project_repository,
    get_recommendation_service,
)
from app.core.config import Settings, get_settings
from app.main import create_app
from app.repositories.json_project_repository import JsonProjectRepository
from app.repositories.memory_lead_repository import MemoryLeadRepository
from app.services.affiliation_service import AffiliationService
from app.services.lead_service import LeadService
from app.services.project_profile_service import ProjectProfileService
from app.services.question_service import QuestionService
from app.services.readiness_service import ReadinessService
from app.services.recommendation_service import RecommendationService
from app.services.summary_service import SummaryService
from fastapi.testclient import TestClient


@pytest.fixture
def api_client(tmp_path: Path) -> TestClient:
    catalog = [
        {
            "id": "00000000-0000-0000-0000-000000000201",
            "nombre": "Agrupación De Vivienda Monguí",
            "ubicacion": "Monguí",
            "municipio": None,
            "departamento": None,
            "disponible": True,
            "brochure_url": "https://example.com/mongui.pdf",
            "recorrido_360_url": None,
            "perfil_historico": {},
            "metadata": {},
        },
        {
            "id": "00000000-0000-0000-0000-000000000202",
            "nombre": "Proyecto Costa",
            "ubicacion": "Cartagena",
            "disponible": True,
            "perfil_historico": {},
            "metadata": {},
        },
        {
            "id": "00000000-0000-0000-0000-000000000203",
            "nombre": "Proyecto Cerrado",
            "ubicacion": "Monguí",
            "disponible": False,
            "perfil_historico": {},
            "metadata": {},
        },
    ]
    profiles = {
        "catalog_profiles": [
            {
                "project_id": "00000000-0000-0000-0000-000000000201",
                "catalog_name": "Agrupación De Vivienda Monguí",
                "total_buyers": 80,
                "affiliated_percentage": 92.0,
                "non_affiliated_percentage": 8.0,
                "salary_range_distribution": {"Entre 1 y 1.5 SMLV": 75.0},
                "segments": {"Básico": 60.0},
                "dependents_distribution": {"1.0": 40.0},
                "household_composition_distribution": {"3.0": 35.0},
                "historical_price_reliable": False,
            },
            {
                "project_id": "00000000-0000-0000-0000-000000000202",
                "catalog_name": "Proyecto Costa",
                "total_buyers": 40,
                "affiliated_percentage": 70.0,
                "non_affiliated_percentage": 30.0,
                "salary_range_distribution": {"Entre 3 y 4 SMLV": 50.0},
                "segments": {"Medio": 55.0},
                "historical_price_reliable": False,
            },
            {
                "project_id": "00000000-0000-0000-0000-000000000203",
                "catalog_name": "Proyecto Cerrado",
                "total_buyers": 20,
                "affiliated_percentage": 90.0,
                "historical_price_reliable": False,
            },
        ]
    }
    catalog_path = tmp_path / "catalog.json"
    profiles_path = tmp_path / "profiles.json"
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    profiles_path.write_text(json.dumps(profiles), encoding="utf-8")

    settings = Settings(
        SMMLV=1_000_000,
        PROJECTS_CATALOG_PATH=str(catalog_path),
        PROJECT_PROFILES_PATH=str(profiles_path),
        PROJECTS_CANONICAL_PATH=str(tmp_path / "missing_canonical.json"),
        PROJECT_ALIASES_PATH=str(tmp_path / "missing_aliases.json"),
    )
    repository = MemoryLeadRepository()
    project_repo = JsonProjectRepository(
        settings=settings,
        catalog_path=catalog_path,
        profiles_path=profiles_path,
    )

    get_settings.cache_clear()
    get_lead_repository.cache_clear()
    get_project_repository.cache_clear()

    app = create_app()

    def override_settings() -> Settings:
        return settings

    def override_lead_repo() -> MemoryLeadRepository:
        return repository

    def override_project_repo() -> JsonProjectRepository:
        return project_repo

    def override_project_service() -> ProjectProfileService:
        return ProjectProfileService(repository=project_repo, settings=settings)

    def override_recommendation_service() -> RecommendationService:
        return RecommendationService(
            project_repository=project_repo,
            project_profile_service=ProjectProfileService(
                repository=project_repo,
                settings=settings,
            ),
            settings=settings,
        )

    def override_lead_service() -> LeadService:
        affiliation = AffiliationService(settings)
        questions = QuestionService()
        readiness = ReadinessService(questions)
        recommendation = override_recommendation_service()
        summary = SummaryService(
            readiness_service=readiness,
            affiliation_service=affiliation,
            recommendation_service=recommendation,
        )
        return LeadService(
            repository=repository,
            affiliation_service=affiliation,
            question_service=questions,
            readiness_service=readiness,
            summary_service=summary,
        )

    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[get_lead_repository] = override_lead_repo
    app.dependency_overrides[get_project_repository] = override_project_repo
    app.dependency_overrides[get_project_profile_service] = override_project_service
    app.dependency_overrides[get_recommendation_service] = override_recommendation_service
    app.dependency_overrides[get_lead_service] = override_lead_service

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    get_settings.cache_clear()
    get_lead_repository.cache_clear()
    get_project_repository.cache_clear()


def test_recommendations_for_existing_lead(api_client: TestClient) -> None:
    created = api_client.post(
        "/api/v1/leads",
        json={
            "nombre": "Ana",
            "afiliado": True,
            "salario_mensual": 1200000,
            "ubicacion_deseada": "Monguí",
            "personas_hogar": 3,
            "personas_a_cargo": 1,
        },
    )
    lead_id = created.json()["id"]
    response = api_client.get(f"/api/v1/leads/{lead_id}/recommendations")
    assert response.status_code == 200
    body = response.json()
    assert body["recommendation_status"] == "completed"
    assert 1 <= len(body["recommended_projects"]) <= 3
    assert body["recommended_projects"][0]["project_name"] == "Agrupación De Vivienda Monguí"
    assert "disclaimer" in body


def test_missing_lead_returns_404(api_client: TestClient) -> None:
    response = api_client.get(f"/api/v1/leads/{uuid4()}/recommendations")
    assert response.status_code == 404


def test_limit_over_10_is_validated(api_client: TestClient) -> None:
    created = api_client.post("/api/v1/leads", json={"afiliado": True})
    lead_id = created.json()["id"]
    response = api_client.get(f"/api/v1/leads/{lead_id}/recommendations?limit=11")
    assert response.status_code == 422


def test_insufficient_information_status(api_client: TestClient) -> None:
    created = api_client.post("/api/v1/leads", json={"nombre": "Sin datos"})
    lead_id = created.json()["id"]
    response = api_client.get(f"/api/v1/leads/{lead_id}/recommendations")
    assert response.status_code == 200
    body = response.json()
    assert body["recommendation_status"] == "insufficient_information"
    assert body["recommended_projects"] == []


def test_projects_list_and_filters(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/projects")
    assert response.status_code == 200
    assert len(response.json()) == 3

    available = api_client.get("/api/v1/projects?disponible=true")
    assert len(available.json()) == 2

    by_name = api_client.get("/api/v1/projects?nombre=mongui")
    assert len(by_name.json()) == 1
    assert "Monguí" in by_name.json()[0]["nombre"]


def test_summary_includes_recommendations(api_client: TestClient) -> None:
    created = api_client.post(
        "/api/v1/leads",
        json={
            "afiliado": True,
            "salario_mensual": 1200000,
            "ubicacion_deseada": "Monguí",
        },
    )
    lead_id = created.json()["id"]
    summary = api_client.get(f"/api/v1/leads/{lead_id}/summary")
    assert summary.status_code == 200
    body = summary.json()
    assert len(body["recommended_projects"]) >= 1
    assert body.get("recommendation_warning") is None
