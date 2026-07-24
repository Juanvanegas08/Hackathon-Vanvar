"""Identity lookup should reuse stored profiles by document."""

from app.models.lead import Lead, LeadStatus
from app.repositories.memory_lead_repository import MemoryLeadRepository
from app.services.identity_service import IdentityService
from app.providers.mock_affiliation_provider import MockAffiliationLookupProvider
from app.core.config import Settings


def test_create_from_identity_reuses_existing_profile() -> None:
    repo = MemoryLeadRepository()
    settings = Settings(
        SMMLV=1_000_000,
        MOCK_AFFILIATES_PATH="data/mock/mock_affiliates.json",
        PERSISTENCE_PROVIDER="memory",
        DATABASE_ENABLED=False,
    )
    service = IdentityService(
        repository=repo,
        provider=MockAffiliationLookupProvider(settings=settings),
    )

    first, ctx1 = service.create_lead_from_identity(
        document_type="CC",
        document_number="1000000001",
        data_consent=True,
    )
    assert ctx1["created"] is True
    first = first.apply_partial_update(
        {
            "ubicacion_deseada": "Chía",
            "ahorro": 15_000_000,
            "estado_lead": LeadStatus.PERFIL_INCOMPLETO,
        }
    )
    repo.save_profile(first)

    second, ctx2 = service.create_lead_from_identity(
        document_type="CC",
        document_number="1000000001",
        data_consent=True,
    )
    assert ctx2["created"] is False
    assert ctx2["profile_source"] == "database"
    assert second.id == first.id
    assert second.ubicacion_deseada == "Chía"
    assert second.ahorro == 15_000_000


def test_create_from_identity_without_consent_resets_existing_profile() -> None:
    repo = MemoryLeadRepository()
    settings = Settings(
        SMMLV=1_000_000,
        MOCK_AFFILIATES_PATH="data/mock/mock_affiliates.json",
        PERSISTENCE_PROVIDER="memory",
        DATABASE_ENABLED=False,
    )
    service = IdentityService(
        repository=repo,
        provider=MockAffiliationLookupProvider(settings=settings),
    )

    first, _ = service.create_lead_from_identity(
        document_type="CC",
        document_number="1000000001",
        data_consent=True,
    )
    first = first.apply_partial_update(
        {
            "ubicacion_deseada": "Chía",
            "ahorro": 15_000_000,
            "ingreso_hogar": 4_000_000,
            "engagement_label": "interesado",
            "engagement_score": 88,
            "engagement_reason": "Muy colaborador",
            "estado_lead": LeadStatus.LISTO_PARA_ASESOR,
        }
    )
    repo.save_profile(first)

    wiped, ctx = service.create_lead_from_identity(
        document_type="CC",
        document_number="1000000001",
        data_consent=False,
    )
    assert ctx["reset"] is True
    assert ctx["profile_source"] == "reset"
    assert wiped.id == first.id
    assert wiped.ubicacion_deseada is None
    assert wiped.ahorro is None
    assert wiped.ingreso_hogar is None
    assert wiped.engagement_label is None
    assert wiped.engagement_score is None
    assert wiped.engagement_reason is None
    assert wiped.estado_lead == LeadStatus.NUEVO
    assert wiped.data_consent is False


def test_lookup_prefers_stored_profile() -> None:
    repo = MemoryLeadRepository()
    lead = Lead(
        document_type="CC",
        document_number="9999999999",
        nombre="Persona Guardada",
        afiliado=True,
        ubicacion_deseada="Ricaurte",
        known_lead=True,
    )
    repo.create(lead)
    service = IdentityService(repository=repo)
    result = service.lookup("CC", "9999999999")
    assert result["known_lead"] is True
    assert result["profile_source"] == "database"
    assert result["prefilled_profile"]["ubicacion_deseada"] == "Ricaurte"
