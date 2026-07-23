"""Tests for mock identity lookup, prefill and confirmations."""

from pathlib import Path

import pytest
from app.api.deps import (
    get_affiliation_provider,
    get_identity_service,
    get_lead_repository,
    get_lead_service,
    get_project_repository,
    get_recommendation_service,
    get_settings_dep,
)
from app.core.config import Settings
from app.main import create_app
from app.providers.mock_affiliation_provider import MockAffiliationLookupProvider
from app.repositories.memory_lead_repository import MemoryLeadRepository
from app.services.affiliation_service import AffiliationService
from app.services.identity_service import IdentityService
from app.services.lead_service import LeadService
from app.services.question_service import QuestionService
from app.services.readiness_service import ReadinessService
from app.services.recommendation_service import RecommendationService
from app.services.summary_service import SummaryService
from fastapi.testclient import TestClient


@pytest.fixture
def identity_client(tmp_path: Path) -> TestClient:
    settings = Settings(
        SMMLV=1_000_000,
        APP_ENV="development",
        MOCK_AFFILIATES_PATH="data/mock/mock_affiliates.json",
        PROJECTS_CANONICAL_PATH=str(tmp_path / "no_canonical.json"),
        PROJECTS_CATALOG_PATH="data/processed/projects_catalog.json",
        PROJECT_PROFILES_PATH="data/processed/project_profiles.json",
        PROJECT_ALIASES_PATH="data/processed/project_aliases.json",
    )
    repository = MemoryLeadRepository()
    provider = MockAffiliationLookupProvider(settings=settings)

    get_lead_repository.cache_clear()
    get_project_repository.cache_clear()
    get_affiliation_provider.cache_clear()

    app = create_app()

    def override_settings() -> Settings:
        return settings

    def override_repo() -> MemoryLeadRepository:
        return repository

    def override_provider() -> MockAffiliationLookupProvider:
        return provider

    def override_identity() -> IdentityService:
        return IdentityService(
            repository=repository,
            provider=provider,
            affiliation_service=AffiliationService(settings),
        )

    def override_lead_service() -> LeadService:
        affiliation = AffiliationService(settings)
        questions = QuestionService()
        readiness = ReadinessService(questions)
        recommendation = RecommendationService(settings=settings)
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

    app.dependency_overrides[get_settings_dep] = override_settings
    app.dependency_overrides[get_lead_repository] = override_repo
    app.dependency_overrides[get_affiliation_provider] = override_provider
    app.dependency_overrides[get_identity_service] = override_identity
    app.dependency_overrides[get_lead_service] = override_lead_service
    app.dependency_overrides[get_recommendation_service] = (
        lambda: RecommendationService(settings=settings)
    )

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    get_lead_repository.cache_clear()
    get_project_repository.cache_clear()
    get_affiliation_provider.cache_clear()


def test_known_affiliate_lookup(identity_client: TestClient) -> None:
    before = identity_client.get("/api/v1/leads")
    assert before.json() == []
    response = identity_client.post(
        "/api/v1/identity/lookup",
        json={"document_type": "CC", "document_number": "1000000001"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["match_status"] == "known_affiliate"
    assert body["known_lead"] is True
    assert body["demo_mode"] is True
    assert "salario_mensual" in body["fields_to_confirm"]
    assert identity_client.get("/api/v1/leads").json() == []


def test_known_non_affiliate_and_new_lead(identity_client: TestClient) -> None:
    non_aff = identity_client.post(
        "/api/v1/identity/lookup",
        json={"document_type": "CC", "document_number": "1000000005"},
    )
    assert non_aff.json()["match_status"] == "known_non_affiliate"
    unknown = identity_client.post(
        "/api/v1/identity/lookup",
        json={"document_type": "CC", "document_number": "9999999999"},
    )
    assert unknown.json()["match_status"] == "new_lead"
    assert unknown.json()["known_lead"] is False


def test_create_without_consent_does_not_prefill_finance(
    identity_client: TestClient,
) -> None:
    response = identity_client.post(
        "/api/v1/leads/from-identity",
        json={
            "document_type": "CC",
            "document_number": "1000000001",
            "data_consent": False,
        },
    )
    assert response.status_code == 201
    lead = response.json()["lead"]
    assert lead["identity_verified"] is False
    assert lead["demo_mode"] is True
    assert lead["salario_mensual"] is None
    assert lead["known_lead"] is True


def test_create_with_consent_prefills_and_asks_confirmation(
    identity_client: TestClient,
) -> None:
    response = identity_client.post(
        "/api/v1/leads/from-identity",
        json={
            "document_type": "CC",
            "document_number": "1000000001",
            "data_consent": True,
        },
    )
    assert response.status_code == 201
    body = response.json()
    lead = body["lead"]
    assert lead["afiliado"] is True
    assert lead["salario_mensual"] == 1800000
    assert lead["identity_verified"] is False
    assert body["next_question"]["type"] == "confirmation"
    assert body["next_question"]["field"] == "salario_mensual"


def test_confirm_and_correct_prefilled_data(identity_client: TestClient) -> None:
    created = identity_client.post(
        "/api/v1/leads/from-identity",
        json={
            "document_type": "CC",
            "document_number": "1000000001",
            "data_consent": True,
        },
    )
    lead_id = created.json()["lead"]["id"]
    response = identity_client.post(
        f"/api/v1/leads/{lead_id}/confirm-prefilled-data",
        json={
            "confirmations": {
                "salario_mensual": {"confirmed": True},
                "personas_a_cargo": {"confirmed": False, "new_value": 2},
            }
        },
    )
    assert response.status_code == 200
    lead = response.json()
    assert "salario_mensual" not in lead["fields_to_confirm"]
    assert "personas_a_cargo" not in lead["fields_to_confirm"]
    assert lead["personas_a_cargo"] == 2
    assert lead["field_metadata"]["personas_a_cargo"]["source"] == "user_declared"
    assert lead["field_metadata"]["salario_mensual"]["confirmed"] is True

    bad = identity_client.post(
        f"/api/v1/leads/{lead_id}/confirm-prefilled-data",
        json={"confirmations": {"ahorro": {"confirmed": True}}},
    )
    assert bad.status_code == 400

    negative = identity_client.post(
        f"/api/v1/leads/{lead_id}/confirm-prefilled-data",
        json={
            "confirmations": {
                "salario_mensual": {"confirmed": False, "new_value": -10}
            }
        },
    )
    # Field already confirmed/removed from confirmables -> 400, or validation path.
    assert negative.status_code in {400, 422}


def test_known_lead_skips_affiliation_question(identity_client: TestClient) -> None:
    created = identity_client.post(
        "/api/v1/leads/from-identity",
        json={
            "document_type": "CC",
            "document_number": "1000000001",
            "data_consent": True,
        },
    )
    lead_id = created.json()["lead"]["id"]
    identity_client.post(
        f"/api/v1/leads/{lead_id}/confirm-prefilled-data",
        json={
            "confirmations": {
                "salario_mensual": {"confirmed": True},
                "personas_a_cargo": {"confirmed": True},
            }
        },
    )
    question = identity_client.get(f"/api/v1/leads/{lead_id}/next-question")
    assert question.status_code == 200
    body = question.json()
    assert body["completed"] is False
    assert body["next_question"]["field"] != "afiliado"
    assert body["next_question"]["field"] == "ingreso_hogar"


def test_summary_and_recommendations_for_known_lead(
    identity_client: TestClient,
) -> None:
    created = identity_client.post(
        "/api/v1/leads/from-identity",
        json={
            "document_type": "CC",
            "document_number": "1000000001",
            "data_consent": True,
        },
    )
    lead_id = created.json()["lead"]["id"]
    identity_client.post(
        f"/api/v1/leads/{lead_id}/confirm-prefilled-data",
        json={
            "confirmations": {
                "salario_mensual": {"confirmed": True},
                "personas_a_cargo": {"confirmed": True},
            }
        },
    )
    identity_client.patch(
        f"/api/v1/leads/{lead_id}",
        json={
            "ingreso_hogar": 3000000,
            "ahorro": 20000000,
            "obligaciones_mensuales": 400000,
            "tiene_vivienda": False,
            "situacion_crediticia": "al_dia",
            "ubicacion_deseada": "Mongui",
            "plazo_compra": "6_meses",
            "proyecto_interes": "Mongui",
        },
    )
    summary = identity_client.get(f"/api/v1/leads/{lead_id}/summary")
    assert summary.status_code == 200
    body = summary.json()
    assert body["identity_context"]["known_lead"] is True
    assert "field_sources" in body
    assert "disclaimer" in body

    rec = identity_client.get(f"/api/v1/leads/{lead_id}/recommendations?limit=3")
    assert rec.status_code == 200
    projects = rec.json()["recommended_projects"]
    canonical_ids = [item["canonical_project_id"] for item in projects]
    assert len(canonical_ids) == len(set(canonical_ids))
    assert rec.json()["disclaimer"]


def test_demo_identities_endpoint(identity_client: TestClient) -> None:
    response = identity_client.get("/api/v1/demo/identities")
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 5
    assert "document_number" in body[0]
    assert "reported_salary" not in body[0]
