"""Shared FastAPI dependencies."""

from functools import lru_cache

from app.repositories.memory_lead_repository import MemoryLeadRepository
from app.services.affiliation_service import AffiliationService
from app.services.lead_service import LeadService
from app.services.question_service import QuestionService
from app.services.readiness_service import ReadinessService
from app.services.summary_service import SummaryService


@lru_cache
def get_lead_repository() -> MemoryLeadRepository:
    """Return the process-wide in-memory repository instance."""
    return MemoryLeadRepository()


def get_lead_service() -> LeadService:
    """Build a LeadService wired to the shared repository."""
    repository = get_lead_repository()
    affiliation = AffiliationService()
    questions = QuestionService()
    readiness = ReadinessService(questions)
    summary = SummaryService(readiness_service=readiness, affiliation_service=affiliation)
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
