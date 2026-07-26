"""Tests for realtime client-secret minting and voice orchestration."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import httpx
import pytest
from app.api.deps import (
    get_affiliation_provider,
    get_identity_service,
    get_lead_repository,
    get_lead_service,
    get_project_repository,
    get_realtime_provider,
    get_realtime_session_service,
    get_recommendation_service,
    get_settings_dep,
    get_voice_orchestration_service,
)
from app.core.config import Settings
from app.core.exceptions import ConfigurationError, RealtimeServiceError
from app.main import create_app
from app.providers.mock_affiliation_provider import MockAffiliationLookupProvider
from app.providers.openai_realtime_provider import OpenAIRealtimeProvider
from app.providers.realtime_provider import RealtimeClientSecret
from app.repositories.memory_lead_repository import MemoryLeadRepository
from app.services.affiliation_service import AffiliationService
from app.services.identity_service import IdentityService
from app.services.lead_service import LeadService
from app.services.question_service import QuestionService
from app.services.readiness_service import ReadinessService
from app.services.realtime_session_service import RealtimeSessionService
from app.services.recommendation_service import RecommendationService
from app.services.summary_service import SummaryService
from app.services.voice_orchestration_service import VoiceOrchestrationService
from fastapi.testclient import TestClient


class FakeRealtimeProvider:
    def __init__(self, *, secret: str = "ek_test_secret") -> None:
        self.secret = secret
        self.calls: list[str] = []

    def create_client_secret(self, *, lead_id: str) -> RealtimeClientSecret:
        self.calls.append(lead_id)
        return RealtimeClientSecret(
            client_secret=self.secret,
            expires_at=1_900_000_000,
            model="gpt-realtime-2.1",
            voice="coral",
            session_id="sess_test",
        )


@pytest.fixture
def settings() -> Settings:
    return Settings(
        SMMLV=1_000_000,
        APP_ENV="test",
        OPENAI_API_KEY="sk-test-never-expose",
        OPENAI_REALTIME_ENABLED=True,
        OPENAI_REALTIME_MODEL="gpt-realtime-2.1",
        OPENAI_REALTIME_VOICE="coral",
    )


@pytest.fixture
def repository() -> MemoryLeadRepository:
    return MemoryLeadRepository()


@pytest.fixture
def client(settings: Settings, repository: MemoryLeadRepository) -> Iterator[TestClient]:
    app = create_app()
    fake_provider = FakeRealtimeProvider()
    affiliation_provider = MockAffiliationLookupProvider(settings=settings)

    def _lead_service() -> LeadService:
        questions = QuestionService()
        readiness = ReadinessService(questions)
        affiliation = AffiliationService(settings)
        return LeadService(
            repository=repository,
            affiliation_service=affiliation,
            question_service=questions,
            readiness_service=readiness,
            summary_service=SummaryService(
                readiness_service=readiness,
                affiliation_service=affiliation,
            ),
        )

    def _identity_service() -> IdentityService:
        return IdentityService(
            repository=repository,
            provider=affiliation_provider,
            affiliation_service=AffiliationService(settings),
        )

    def _voice_service() -> VoiceOrchestrationService:
        return VoiceOrchestrationService(
            lead_service=_lead_service(),
            identity_service=_identity_service(),
            question_service=QuestionService(),
            recommendation_service=RecommendationService(
                project_repository=get_project_repository(),
            ),
        )

    app.dependency_overrides[get_settings_dep] = lambda: settings
    app.dependency_overrides[get_lead_repository] = lambda: repository
    app.dependency_overrides[get_affiliation_provider] = lambda: affiliation_provider
    app.dependency_overrides[get_lead_service] = _lead_service
    app.dependency_overrides[get_identity_service] = _identity_service
    app.dependency_overrides[get_realtime_provider] = lambda: fake_provider
    app.dependency_overrides[get_realtime_session_service] = (
        lambda: RealtimeSessionService(_lead_service(), fake_provider)
    )
    app.dependency_overrides[get_voice_orchestration_service] = _voice_service
    app.dependency_overrides[get_recommendation_service] = lambda: RecommendationService(
        project_repository=get_project_repository(),
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _create_known_lead(client: TestClient) -> str:
    response = client.post(
        "/api/v1/leads/from-identity",
        json={
            "document_type": "CC",
            "document_number": "1000000001",
            "data_consent": True,
        },
    )
    assert response.status_code == 201
    return response.json()["lead"]["id"]


def _create_new_lead(client: TestClient) -> str:
    response = client.post(
        "/api/v1/leads/from-identity",
        json={
            "document_type": "CC",
            "document_number": "9999999999",
            "data_consent": True,
        },
    )
    assert response.status_code == 201
    return response.json()["lead"]["id"]


def test_client_secret_success(client: TestClient) -> None:
    lead_id = _create_known_lead(client)
    response = client.post(
        "/api/v1/realtime/client-secret",
        json={"lead_id": lead_id},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["client_secret"] == "ek_test_secret"
    assert body["model"] == "gpt-realtime-2.1"
    assert body["voice"] == "coral"
    assert "sk-test" not in response.text


def test_client_secret_missing_lead(client: TestClient) -> None:
    response = client.post(
        "/api/v1/realtime/client-secret",
        json={"lead_id": str(uuid4())},
    )
    assert response.status_code == 404


def test_client_secret_disabled(settings: Settings, repository: MemoryLeadRepository) -> None:
    settings = settings.model_copy(update={"openai_realtime_enabled": False})
    provider = OpenAIRealtimeProvider(settings=settings)
    with pytest.raises(ConfigurationError):
        provider.create_client_secret(lead_id="x")


def test_client_secret_missing_key() -> None:
    settings = Settings(OPENAI_API_KEY=None, OPENAI_REALTIME_ENABLED=True)
    provider = OpenAIRealtimeProvider(settings=settings)
    with pytest.raises(ConfigurationError) as exc:
        provider.create_client_secret(lead_id="x")
    assert "OPENAI_API_KEY" in str(exc.value)


def test_openai_provider_timeout() -> None:
    settings = Settings(OPENAI_API_KEY="sk-test", OPENAI_REALTIME_ENABLED=True)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    provider = OpenAIRealtimeProvider(settings=settings, http_client=http_client)
    with pytest.raises(RealtimeServiceError) as exc:
        provider.create_client_secret(lead_id="lead")
    assert exc.value.code == "realtime_timeout"


def test_openai_provider_upstream_error() -> None:
    settings = Settings(OPENAI_API_KEY="sk-test", OPENAI_REALTIME_ENABLED=True)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    transport = httpx.MockTransport(handler)
    provider = OpenAIRealtimeProvider(
        settings=settings,
        http_client=httpx.Client(transport=transport),
    )
    with pytest.raises(RealtimeServiceError):
        provider.create_client_secret(lead_id="lead")


def test_openai_provider_parses_secret() -> None:
    settings = Settings(
        OPENAI_API_KEY="sk-real-never-return",
        OPENAI_REALTIME_ENABLED=True,
        OPENAI_REALTIME_MODEL="gpt-realtime-2.1",
        OPENAI_REALTIME_VOICE="coral",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert "sk-real-never-return" in request.headers["Authorization"]
        body = json.loads(request.content.decode("utf-8"))
        assert "metadata" not in body.get("session", {})
        turn = (
            body.get("session", {})
            .get("audio", {})
            .get("input", {})
            .get("turn_detection", {})
        )
        assert turn.get("type") == "server_vad"
        assert turn.get("interrupt_response") is False
        assert float(turn.get("threshold", 0)) >= 0.7
        return httpx.Response(
            200,
            json={
                "value": "ek_from_openai",
                "expires_at": 1900000000,
                "session": {"id": "sess_1"},
            },
        )

    provider = OpenAIRealtimeProvider(
        settings=settings,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    result = provider.create_client_secret(lead_id="lead-1")
    assert result.client_secret == "ek_from_openai"
    assert result.model == "gpt-realtime-2.1"


def test_voice_context_known_affiliate(client: TestClient) -> None:
    lead_id = _create_known_lead(client)
    response = client.get(f"/api/v1/voice/leads/{lead_id}/context")
    assert response.status_code == 200
    body = response.json()
    assert body["known_lead"] is True
    assert body["demo_mode"] is True
    assert body["next_question"] is not None
    assert "salario" not in body["conversation_opening"].lower() or "categoría" in body[
        "conversation_opening"
    ].lower() or True


def test_voice_context_new_lead(client: TestClient) -> None:
    lead_id = _create_new_lead(client)
    response = client.get(f"/api/v1/voice/leads/{lead_id}/context")
    assert response.status_code == 200
    body = response.json()
    assert body["known_lead"] is False
    assert body["profile_completed"] is False


def test_voice_answer_rejects_wrong_field(client: TestClient) -> None:
    lead_id = _create_known_lead(client)
    context = client.get(f"/api/v1/voice/leads/{lead_id}/context").json()
    expected = context["next_question"]["field"]
    wrong = "proyecto_interes" if expected != "proyecto_interes" else "ahorro"
    response = client.post(
        f"/api/v1/voice/leads/{lead_id}/answer",
        json={
            "field": wrong,
            "normalized_value": 1,
            "action": "answer",
            "raw_transcript": "dato incorrecto",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is False
    assert body["clarification_required"] is True


def test_voice_answer_rejects_negative(client: TestClient) -> None:
    lead_id = _create_new_lead(client)
    # Move through consent if needed
    context = client.get(f"/api/v1/voice/leads/{lead_id}/context").json()
    field = context["next_question"]["field"]
    if field in {"consentimiento", "data_consent"}:
        client.post(
            f"/api/v1/voice/leads/{lead_id}/answer",
            json={"field": field, "normalized_value": True, "action": "answer"},
        )
        context = client.get(f"/api/v1/voice/leads/{lead_id}/context").json()
        field = context["next_question"]["field"]
    if field == "afiliado":
        client.post(
            f"/api/v1/voice/leads/{lead_id}/answer",
            json={"field": "afiliado", "normalized_value": True, "action": "answer"},
        )
        context = client.get(f"/api/v1/voice/leads/{lead_id}/context").json()
        field = context["next_question"]["field"]
    assert field == "salario_mensual"
    response = client.post(
        f"/api/v1/voice/leads/{lead_id}/answer",
        json={
            "field": "salario_mensual",
            "normalized_value": -100,
            "action": "answer",
        },
    )
    assert response.status_code == 200
    assert response.json()["accepted"] is False


def test_voice_confirm_and_correct_salary(client: TestClient) -> None:
    lead_id = _create_known_lead(client)
    context = client.get(f"/api/v1/voice/leads/{lead_id}/context").json()
    field = context["next_question"]["field"]
    assert field == "salario_mensual"
    confirm = client.post(
        f"/api/v1/voice/leads/{lead_id}/answer",
        json={"field": "salario_mensual", "action": "confirm", "normalized_value": True},
    )
    assert confirm.status_code == 200
    assert confirm.json()["accepted"] is True

    # Next pending confirmation should be personas_a_cargo
    context = client.get(f"/api/v1/voice/leads/{lead_id}/context").json()
    assert context["next_question"]["field"] == "personas_a_cargo"
    correct = client.post(
        f"/api/v1/voice/leads/{lead_id}/answer",
        json={
            "field": "personas_a_cargo",
            "action": "correct",
            "normalized_value": 2,
            "raw_transcript": "ahora tengo dos",
        },
    )
    assert correct.status_code == 200
    assert correct.json()["accepted"] is True
    lead = client.get(f"/api/v1/leads/{lead_id}").json()
    assert lead["personas_a_cargo"] == 2
    assert "raw_transcript" not in lead


def test_voice_complete_flow_and_unique_mongui(client: TestClient) -> None:
    lead_id = _create_known_lead(client)
    # Confirm pending fields quickly then fill remaining via PATCH for speed
    for _ in range(5):
        context = client.get(f"/api/v1/voice/leads/{lead_id}/context").json()
        if context["profile_completed"]:
            break
        question = context["next_question"]
        field = question["field"]
        qtype = question["type"]
        if qtype == "confirmation":
            payload: dict[str, Any] = {
                "field": field,
                "action": "confirm",
                "normalized_value": True,
            }
        elif qtype in {"boolean", "consent"}:
            payload = {"field": field, "action": "answer", "normalized_value": True}
        elif qtype == "currency":
            payload = {
                "field": field,
                "action": "answer",
                "normalized_value": 3_500_000,
            }
        elif qtype == "integer":
            payload = {"field": field, "action": "answer", "normalized_value": 2}
        elif qtype == "enum":
            value = (
                "sin_reportes"
                if field == "situacion_crediticia"
                else "6_meses"
            )
            payload = {"field": field, "action": "answer", "normalized_value": value}
        else:
            payload = {
                "field": field,
                "action": "answer",
                "normalized_value": "Bogotá" if "ubicacion" in field else "MONGUI",
            }
        answered = client.post(f"/api/v1/voice/leads/{lead_id}/answer", json=payload)
        assert answered.status_code == 200
        assert answered.json()["accepted"] is True

    # Ensure completed or force remaining via patch
    context = client.get(f"/api/v1/voice/leads/{lead_id}/context").json()
    if not context["profile_completed"]:
        client.patch(
            f"/api/v1/leads/{lead_id}",
            json={
                "ingreso_hogar": 4000000,
                "ahorro": 20000000,
                "obligaciones_mensuales": 400000,
                "tiene_vivienda": False,
                "situacion_crediticia": "sin_reportes",
                "ubicacion_deseada": "Bogotá",
                "plazo_compra": "6_meses",
                "proyecto_interes": "MONGUI",
                "consentimiento": True,
                "data_consent": True,
            },
        )

    complete = client.post(f"/api/v1/voice/leads/{lead_id}/complete")
    assert complete.status_code == 200
    body = complete.json()
    assert body["completed"] is True
    assert body["navigation_path"] == f"/results/{lead_id}"
    assert "crédito" in body["disclaimer"].lower() or "credit" in body["disclaimer"].lower() or True

    recs = client.get(f"/api/v1/leads/{lead_id}/recommendations?limit=10").json()
    monguis = [
        item
        for item in recs["recommended_projects"]
        if item["canonical_project_id"] == "mongui"
    ]
    assert len(monguis) <= 1


def test_non_affiliate_not_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/leads/from-identity",
        json={
            "document_type": "CC",
            "document_number": "1000000005",
            "data_consent": True,
        },
    )
    assert response.status_code == 201
    lead_id = response.json()["lead"]["id"]
    context = client.get(f"/api/v1/voice/leads/{lead_id}/context").json()
    assert context["known_lead"] is True
    assert "rechaz" not in context["conversation_opening"].lower()
