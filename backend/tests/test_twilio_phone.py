"""Tests for Twilio phone channel helpers and APIs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import UUID, uuid4

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
from app.models.lead import CanalOrigen, DocumentType, Lead
from app.models.scheduled_call import ScheduledCallStatus
from app.repositories.memory_lead_repository import MemoryLeadRepository
from app.services.affiliation_service import AffiliationService
from app.services.identity_service import IdentityService
from app.services.lead_service import LeadService
from app.services.phone_call_orchestrator import PhoneCallOrchestrator
from app.services.phone_laura_agent import (
    default_welcome_greeting,
    find_lead_by_phone,
    web_tool_names,
)
from app.services.twilio_call_service import sanitize_elevenlabs_voice
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
        TWILIO_VOICE_MODE="gather",
        TWILIO_TTS_PROVIDER="Google",
        TWILIO_TTS_VOICE="es-US-Chirp3-HD-Aoede",
        TWILIO_TRANSCRIPTION_PROVIDER="Google",
        OPENAI_API_KEY="sk-test",
        PERSISTENCE_PROVIDER="memory",
        DATABASE_ENABLED=False,
    )


def test_normalize_phone_colombia() -> None:
    assert normalize_phone("3012874982") == "+573012874982"
    assert normalize_phone("+57 301 287 4982") == "+573012874982"
    assert normalize_phone("3012874982", country_code="57") == "+573012874982"
    assert normalize_phone("5551234567", country_code="1") == "+15551234567"


def test_phone_last4_and_callable_helpers() -> None:
    from app.utils.phone import (
        is_reassignable_demo_phone,
        phone_last4,
        resolve_callable_phone,
    )

    assert phone_last4("+573224347771") == "7771"
    assert phone_last4("***4138") == "4138"
    assert resolve_callable_phone("7771") is None
    assert resolve_callable_phone("+573224347771") == "+573224347771"
    assert is_reassignable_demo_phone("+573224347771")
    assert not is_reassignable_demo_phone("+573001112233")


def test_candidate_identifier_hashes_include_seed_format() -> None:
    from app.utils.identity_hash import (
        candidate_identifier_hashes,
        seed_identifier_hash,
    )

    hashes = candidate_identifier_hashes(
        document_type="CC",
        document_number="9000004138",
        pepper="casalista-dev-pepper",
    )
    assert seed_identifier_hash(
        document_type="CC",
        document_number="9000004138",
    ) in hashes
    assert (
        seed_identifier_hash(document_type="CC", document_number="9000004138")
        == "bbab9d358e969a623fa5921a85a8f16ad6c7b3a055931f5427135c762164d7a5"
    )


def test_build_gather_twiml_includes_lead(
    twilio_settings: Settings,
) -> None:
    service = TwilioCallService(settings=twilio_settings)
    lead_id = uuid4()
    xml = service.build_gather_twiml(
        lead_id=lead_id,
        say_text="Hola",
        needs_identity=False,
    )
    assert "Gather" in xml
    assert "Hola" in xml
    assert "es-MX" in xml
    assert str(lead_id) in xml
    assert "/twilio/voice/turn" in xml


def test_build_conversation_relay_twiml_interruptible(
    twilio_settings: Settings,
) -> None:
    service = TwilioCallService(settings=twilio_settings)
    lead_id = uuid4()
    xml = service.build_conversation_relay_twiml(
        lead_id=lead_id,
        welcome_greeting="Hola, soy Laura",
        needs_identity=False,
        caller_phone="+573001112233",
    )
    assert "ConversationRelay" in xml
    assert 'interruptible="speech"' in xml
    assert 'welcomeGreetingInterruptible="any"' in xml
    assert "wss://example.test/api/v1/twilio/conversation-relay" in xml
    assert "Hola, soy Laura" in xml
    assert str(lead_id) in xml
    assert 'ttsProvider="Google"' in xml
    assert "Chirp3" in xml or "Neural2" in xml
    assert 'language="es-US"' in xml
    assert 'ignoreBackchannel="true"' in xml
    assert 'speechModel="nova-2-general"' in xml
    assert 'speechTimeout="600"' in xml or 'speechTimeout="800"' in xml
    assert 'interruptSensitivity="medium"' in xml
    connect_idx = xml.find("<Connect")
    assert connect_idx > 0
    assert xml.find("<Say", 0, connect_idx) == -1
    assert "<Say" in xml[connect_idx:]


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


def test_laura_instructions_are_one_question_web_parity() -> None:
    from app.services.laura_agent_instructions import (
        AGENT_INSTRUCTIONS,
        build_laura_instructions,
    )

    assert "una pregunta principal a la vez" in AGENT_INSTRUCTIONS.lower()
    assert "y también" not in AGENT_INSTRUCTIONS.lower()
    assert "Agrupa EXACTAMENTE 2" not in AGENT_INSTRUCTIONS
    assert "12 palabras" in AGENT_INSTRUCTIONS.lower()
    assert "menús" in AGENT_INSTRUCTIONS.lower() or "menus" in AGENT_INSTRUCTIONS.lower()
    built = build_laura_instructions(display_name="Ana")
    assert "Ana" in built
    assert "get_voice_context" in built


def test_default_welcome_greeting() -> None:
    none_greeting = default_welcome_greeting(display_name=None, needs_identity=True)
    assert "Laura" in none_greeting
    assert "Colsubsidio" in none_greeting
    named = default_welcome_greeting(display_name="Ana", needs_identity=False)
    assert "Ana" in named
    assert "Laura" in named


def test_sanitize_elevenlabs_voice_keeps_model_suffix() -> None:
    assert (
        sanitize_elevenlabs_voice(
            "b2htR0pMe28pYwCY9gnP-flash_v2_5-1.05_0.55_0.75"
        )
        == "b2htR0pMe28pYwCY9gnP-flash_v2_5-1.05_0.55_0.75"
    )
    assert sanitize_elevenlabs_voice("es-US-Chirp3-HD-Aoede") == "es-US-Chirp3-HD-Aoede"
    assert (
        sanitize_elevenlabs_voice("b2htR0pMe28pYwCY9gnP?foo=1")
        == "b2htR0pMe28pYwCY9gnP"
    )


def test_web_tool_names_match_realtime_agent() -> None:
    assert web_tool_names() == [
        "get_voice_context",
        "submit_current_answer",
        "report_user_engagement",
        "complete_voice_profile",
    ]


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
    assert "Gather" in response.text
    assert "es-MX" in response.text
    assert "/twilio/voice/turn" in response.text
    app.dependency_overrides.clear()


def test_phone_lookup_and_confirm_stored_call(
    twilio_settings: Settings,
    lead_service: LeadService,
    memory_repo: MemoryLeadRepository,
) -> None:
    memory_repo.create(
        Lead(
            nombre="Ana Pérez",
            telefono="+573224347771",
            document_type=DocumentType.CC,
            document_number="900001",
            canal_origen=CanalOrigen.OTRO,
        )
    )
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
    lookup = client.post(
        "/api/v1/phone/lookup",
        json={"document_type": "CC", "document_number": "900001"},
    )
    assert lookup.status_code == 200, lookup.text
    lookup_body = lookup.json()
    assert lookup_body["known_lead"] is True
    assert lookup_body["has_phone"] is True
    assert lookup_body["phone_last4"] == "7771"
    assert lookup_body["nombre"] == "Ana Pérez"

    response = client.post(
        "/api/v1/phone/calls",
        json={
            "mode": "now",
            "document_type": "CC",
            "document_number": "900001",
            "data_consent": True,
            "confirm_stored_phone": True,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["call_sid"] == "CAoutbound123"
    assert body["phone"] == "+573224347771"
    twilio.start_outbound.assert_called_once()
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
    lookup = client.post(
        "/api/v1/phone/lookup",
        json={"document_type": "CC", "document_number": "900001"},
    )
    assert lookup.status_code == 200
    assert lookup.json()["known_lead"] is False

    response = client.post(
        "/api/v1/phone/calls",
        json={
            "nombre": "Ana Pérez",
            "country_code": "57",
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
    lead = lead_service.get_lead(UUID(body["lead_id"]))
    assert lead.nombre == "Ana Pérez"
    assert lead.telefono == "+573001112233"
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
            "nombre": "Carlos Ruiz",
            "country_code": "57",
            "phone": "3001112233",
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
