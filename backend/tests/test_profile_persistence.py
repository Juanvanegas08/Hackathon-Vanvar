"""Tests for profile document serialization (DB / LLM payload)."""

from app.models.lead import CreditSituation, Lead, PurchaseTimeline
from app.services.profile_persistence_service import ProfilePersistenceService


def test_build_organized_profile() -> None:
    service = ProfilePersistenceService()
    lead = Lead(
        nombre="Ana Pérez",
        afiliado=True,
        salario_mensual=2_500_000,
        ahorro=10_000_000,
        ubicacion_deseada="Chía",
        situacion_crediticia=CreditSituation.AL_DIA,
        plazo_compra=PurchaseTimeline.SEIS_MESES,
    )
    document = service.build_document(lead)
    assert document["entity"] == "lead_profile"
    assert document["contact"]["nombre"] == "Ana Pérez"
    assert document["financial"]["salario_mensual"] == 2_500_000
    assert document["credit"]["situacion_crediticia"] == "al_dia"
    assert document["housing_preferences"]["ubicacion_deseada"] == "Chía"
