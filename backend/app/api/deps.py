"""Shared FastAPI dependencies."""

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.providers.mock_affiliation_provider import MockAffiliationLookupProvider
from app.providers.openai_realtime_provider import OpenAIRealtimeProvider
from app.repositories.json_project_repository import JsonProjectRepository
from app.repositories.memory_lead_repository import MemoryLeadRepository
from app.services.affiliation_service import AffiliationService
from app.services.identity_service import IdentityService
from app.services.lead_service import LeadService
from app.services.project_profile_service import ProjectProfileService
from app.services.question_service import QuestionService
from app.services.readiness_service import ReadinessService
from app.services.realtime_session_service import RealtimeSessionService
from app.services.recommendation_service import RecommendationService
from app.services.summary_service import SummaryService
from app.services.voice_orchestration_service import VoiceOrchestrationService


@lru_cache
def get_lead_repository() -> MemoryLeadRepository:
    """Return the process-wide in-memory repository instance."""
    return MemoryLeadRepository()


@lru_cache
def get_project_repository() -> JsonProjectRepository:
    """Return the process-wide JSON project repository."""
    return JsonProjectRepository()


@lru_cache
def get_affiliation_provider() -> MockAffiliationLookupProvider:
    """Return the mock affiliation lookup provider."""
    return MockAffiliationLookupProvider()


def get_settings_dep() -> Settings:
    """FastAPI-friendly settings dependency."""
    return get_settings()


def get_project_profile_service() -> ProjectProfileService:
    """Return project profile service."""
    return ProjectProfileService(repository=get_project_repository())


def get_recommendation_service() -> RecommendationService:
    """Return recommendation service."""
    return RecommendationService(
        project_repository=get_project_repository(),
        project_profile_service=get_project_profile_service(),
    )


def get_identity_service() -> IdentityService:
    """Return identity service wired to the shared lead repository."""
    return IdentityService(
        repository=get_lead_repository(),
        provider=get_affiliation_provider(),
        affiliation_service=AffiliationService(),
    )


def get_lead_service() -> LeadService:
    """Build a LeadService wired to the shared repository."""
    repository = get_lead_repository()
    affiliation = AffiliationService()
    questions = QuestionService()
    readiness = ReadinessService(questions)
    recommendation = get_recommendation_service()
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


def get_affiliation_service() -> AffiliationService:
    """Return affiliation service."""
    return AffiliationService()


def get_realtime_provider() -> OpenAIRealtimeProvider:
    """Return OpenAI Realtime client-secret provider."""
    return OpenAIRealtimeProvider(settings=get_settings())


def get_realtime_session_service() -> RealtimeSessionService:
    """Return realtime session orchestration service."""
    return RealtimeSessionService(
        lead_service=get_lead_service(),
        provider=get_realtime_provider(),
    )


def get_voice_orchestration_service() -> VoiceOrchestrationService:
    """Return voice-facing orchestration service."""
    return VoiceOrchestrationService(
        lead_service=get_lead_service(),
        identity_service=get_identity_service(),
        question_service=QuestionService(),
        recommendation_service=get_recommendation_service(),
    )
