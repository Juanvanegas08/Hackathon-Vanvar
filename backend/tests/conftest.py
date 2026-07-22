"""Shared pytest fixtures."""

from collections.abc import Iterator

import pytest
from app.api.deps import get_affiliation_service, get_lead_repository, get_lead_service
from app.core.config import Settings, get_settings
from app.main import create_app
from app.repositories.memory_lead_repository import MemoryLeadRepository
from app.services.affiliation_service import AffiliationService
from app.services.lead_service import LeadService
from app.services.question_service import QuestionService
from app.services.readiness_service import ReadinessService
from app.services.summary_service import SummaryService
from fastapi.testclient import TestClient


@pytest.fixture
def smmlv_settings() -> Settings:
    """Settings with a known SMMLV for category tests."""
    return Settings(SMMLV=1_000_000, APP_NAME="CasaLista Voice API")


@pytest.fixture
def repository() -> MemoryLeadRepository:
    repo = MemoryLeadRepository()
    repo.clear()
    return repo


@pytest.fixture
def client(repository: MemoryLeadRepository, smmlv_settings: Settings) -> Iterator[TestClient]:
    get_settings.cache_clear()
    get_lead_repository.cache_clear()

    app = create_app()

    def override_settings() -> Settings:
        return smmlv_settings

    def override_repository() -> MemoryLeadRepository:
        return repository

    def override_affiliation_service() -> AffiliationService:
        return AffiliationService(smmlv_settings)

    def override_lead_service() -> LeadService:
        affiliation = AffiliationService(smmlv_settings)
        questions = QuestionService()
        readiness = ReadinessService(questions)
        summary = SummaryService(
            readiness_service=readiness,
            affiliation_service=affiliation,
        )
        return LeadService(
            repository=repository,
            affiliation_service=affiliation,
            question_service=questions,
            readiness_service=readiness,
            summary_service=summary,
        )

    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[get_lead_repository] = override_repository
    app.dependency_overrides[get_affiliation_service] = override_affiliation_service
    app.dependency_overrides[get_lead_service] = override_lead_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    get_settings.cache_clear()
    get_lead_repository.cache_clear()
