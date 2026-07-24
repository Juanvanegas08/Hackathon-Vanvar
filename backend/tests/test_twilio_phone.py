"""Tests for Twilio phone channel helpers and APIs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from app.api.deps import (
    get_identity_service,
    get_lead_service,
    get_phone_call_orchestrator,
    get_scheduled_call_service,
    get_settings_dep,
    get_twilio_call_service,
)
from app.core.config import Settings
from app.main import create_app
from app.models.lead import CanalOrigen, Lead
from app.models.scheduled_call import ScheduledCallStatus
from app.repositories.memory_lead_repository import MemoryLeadRepository
from app.services.affiliation_service import AffiliationService
from app.services.identity_service import IdentityService
from app.services.lead_service import LeadService
from app.services.phone_call_orchestrator import PhoneCallOrchestrator
from app.services.phone_laura_agent import (
    default_welcome_greeting,
    find_lead_by_phone,
)
from app.services.question_service import QuestionService
from app.services.readiness_service import ReadinessService
from app.services.recommendation_service import RecommendationService
from app.services.scheduled_call_service import ScheduledCallService
from app.services.summary_service import SummaryService
from app.services.twilio_call_service import TwilioCallService
from app.utils.phone import normalize_phone
from fastapi.testclient import TestClient


@pytest.fixture()
def memory_repo() -> MemoryLeadRepository:
    return MemoryLeadRepository()


@pytest.fixture()
def lead_service(memory_repo: MemoryLeadRepository) -> LeadService:
    questions = QuestionService()
    readiness = ReadinessService(questions)
    affiliation = AffiliationService()
    recommendation = RecommendationService(
        project_repository=MagicMock(),
        project_profile_service=MagicMock(),
    )
    summary = SummaryService(
        readiness_service=readiness,
        affiliation_service=affiliation,
        recommendation_service=recommendation,
    )
    return LeadService(
        repository=memory_repo,
        affiliation_service=affiliation,
        question_service=questions,
        readiness_service=readiness,
        summary_service=summary,
    )


@pytest.fixture()
def twilio_settings() -> Settings:
    return Settings(
        TWILIO_ACCOUNT_SID="ACffffffffffffffffffffffffffffffff",
        TWILIO_AUTH_TOKEN="test_auth_token_1234567890",
        TWILIO_PHONE_NUMBER="+13203857702",
        TWILIO_PUBLIC_BASE_URL="https://example.test",
        TWILIO_VALIDATE_SIGNATURE=False,
        OPENAI_API_KEY="sk-test",
        PERSISTENCE_PROVIDER="memory",
        DATABASE_ENABLED=False,
    )


def test_normalize_phone_colombia() -> None:
    assert normalize_phone("3012874982") == "+573012874982"
    assert normalize_phone("+57 301 287 4982") == "+573012874982"


def test_build_conversation_relay_twiml_includes_lead(
    twilio_settings: Settings,
) -> None:
    service = TwilioCallService(settings=twilio_settings)
    lead_id = uuid4()
    xml = service.build_conversation_relay_twiml(
        lead_id=lead_id,
        welcome_greeting="Hola",
        needs_identity=False,
        caller_phone="+573001112233",
    )
    assert "ConversationRelay" in xml
    assert "wss://example.test/api/v1/twilio/conversation-relay" in xml
    assert str(lead_id) in xml
    assert "Hola" in xml
    assert "es-MX" in xml


def test_find_lead_by_phone(lead_service: LeadService) -> None:
    lead = Lead(telefono="+573001112233", canal_origen=CanalOrigen.OTRO)
    created = lead_service._repository.create(lead)  # noqa: SLF001
    found = find_lead_by_phone(lead_service, "3001112233")
    assert found is not None
    assert found.id == created.id


def test_scheduled_call_claim_due() -> None:
    store = ScheduledCallService()
    lead_id = uuid4()
    past = datetime.now(UTC) - timedelta(minutes=1)
    future = datetime.now(UTC) + timedelta(hours=1)
    due = store.schedule(lead_id=lead_id, phone="+573001112233", scheduled_at=past)
    store.schedule(lead_id=lead_id, phone="+573001112244", scheduled_at=future)
    claimed = store.claim_due()
    assert len(claimed) == 1
    assert claimed[0].id == due.id
    assert claimed[0].status == ScheduledCallStatus.IN_PROGRESS


def test_default_welcome_greeting() -> None:
    assert "documento" in default_welcome_greeting(
        display_name=None,
        needs_identity=True,
    ).lower()
    assert "Laura" in default_welcome_greeting(display_name="Ana", needs_identity=False)


def test_inbound_twiml_endpoint(
    twilio_settings: Settings,
    lead_service: LeadService,
    memory_repo: MemoryLeadRepository,
) -> None:
    app = create_app()
    scheduled = ScheduledCallService()
    twilio = TwilioCallService(settings=twilio_settings)
    identity = IdentityService(repository=memory_repo)

    app.dependency_overrides[get_settings_dep] = lambda: twilio_settings
    app.dependency_overrides[get_twilio_call_service] = lambda: twilio
    app.dependency_overrides[get_lead_service] = lambda: lead_service
    app.dependency_overrides[get_scheduled_call_service] = lambda: scheduled
    app.dependency_overrides[get_identity_service] = lambda: identity

    client = TestClient(app)
    response = client.post(
        "/api/v1/twilio/voice/inbound",
        data={"From": "+573009998877", "To": "+13203857702", "CallSid": "CAtest"},
    )
    assert response.status_code == 200
    assert "ConversationRelay" in response.text
    assert "needs_identity" in response.text
    app.dependency_overrides.clear()


def test_phone_calls_now_uses_twilio(
    twilio_settings: Settings,
    lead_service: LeadService,
    memory_repo: MemoryLeadRepository,
) -> None:
    app = create_app()
    scheduled = ScheduledCallService()
    twilio = MagicMock(spec=TwilioCallService)
    twilio.start_outbound.return_value = "CAoutbound123"
    identity = IdentityService(repository=memory_repo)
    orchestrator = PhoneCallOrchestrator(
        identity_service=identity,
        lead_service=lead_service,
        twilio_call_service=twilio,
        scheduled_call_service=scheduled,
    )

    app.dependency_overrides[get_settings_dep] = lambda: twilio_settings
    app.dependency_overrides[get_phone_call_orchestrator] = lambda: orchestrator
    app.dependency_overrides[get_lead_service] = lambda: lead_service
    app.dependency_overrides[get_identity_service] = lambda: identity

    client = TestClient(app)
    response = client.post(
        "/api/v1/phone/calls",
        json={
            "phone": "3001112233",
            "mode": "now",
            "document_type": "CC",
            "document_number": "900001",
            "data_consent": True,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mode"] == "now"
    assert body["call_sid"] == "CAoutbound123"
    assert body["phone"] == "+573001112233"
    twilio.start_outbound.assert_called_once()
    app.dependency_overrides.clear()


def test_phone_calls_schedule(
    twilio_settings: Settings,
    lead_service: LeadService,
    memory_repo: MemoryLeadRepository,
) -> None:
    app = create_app()
    scheduled = ScheduledCallService()
    twilio = MagicMock(spec=TwilioCallService)
    identity = IdentityService(repository=memory_repo)
    orchestrator = PhoneCallOrchestrator(
        identity_service=identity,
        lead_service=lead_service,
        twilio_call_service=twilio,
        scheduled_call_service=scheduled,
    )
    app.dependency_overrides[get_phone_call_orchestrator] = lambda: orchestrator

    when = (datetime.now(UTC) + timedelta(minutes=10)).isoformat()
    client = TestClient(app)
    response = client.post(
        "/api/v1/phone/calls",
        json={
            "phone": "+573001112233",
            "mode": "schedule",
            "scheduled_at": when,
            "document_type": "CC",
            "document_number": "900002",
            "data_consent": True,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mode"] == "schedule"
    assert body["scheduled_call_id"]
    assert body["status"] == "pending"
    twilio.start_outbound.assert_not_called()
    app.dependency_overrides.clear()


def test_process_due_scheduled_calls(
    lead_service: LeadService,
    memory_repo: MemoryLeadRepository,
) -> None:
    scheduled = ScheduledCallService()
    twilio = MagicMock(spec=TwilioCallService)
    twilio.start_outbound.return_value = "CAsched"
    identity = IdentityService(repository=memory_repo)
    orchestrator = PhoneCallOrchestrator(
        identity_service=identity,
        lead_service=lead_service,
        twilio_call_service=twilio,
        scheduled_call_service=scheduled,
    )
    lead = memory_repo.create(Lead(telefono="+573001112233"))
    item = scheduled.schedule(
        lead_id=lead.id,
        phone="+573001112233",
        scheduled_at=datetime.now(UTC) - timedelta(seconds=5),
    )
    claimed = orchestrator.process_due_scheduled_calls()
    assert len(claimed) == 1
    assert scheduled.get(item.id) is not None
    assert scheduled.get(item.id).status == ScheduledCallStatus.COMPLETED  # type: ignore[union-attr]
    twilio.start_outbound.assert_called_once()
