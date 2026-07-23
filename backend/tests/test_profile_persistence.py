"""Tests for profile JSON persistence."""

from pathlib import Path

from app.models.lead import CreditSituation, Lead, PurchaseTimeline
from app.services.profile_persistence_service import ProfilePersistenceService
from app.core.config import Settings


def test_save_organized_profile(tmp_path: Path) -> None:
    settings = Settings(LEAD_PROFILES_PATH=str(tmp_path))
    service = ProfilePersistenceService(settings=settings)
    lead = Lead(
        nombre="Ana Pérez",
        afiliado=True,
        salario_mensual=2_500_000,
        ahorro=10_000_000,
        ubicacion_deseada="Chía",
        situacion_crediticia=CreditSituation.AL_DIA,
        plazo_compra=PurchaseTimeline.SEIS_MESES,
    )
    path = service.save_lead_profile(lead)
    assert path.exists()
    document = service.load_lead_profile(lead.id)
    assert document is not None
    assert document["entity"] == "lead_profile"
    assert document["contact"]["nombre"] == "Ana Pérez"
    assert document["financial"]["salario_mensual"] == 2_500_000
    assert document["credit"]["situacion_crediticia"] == "al_dia"
    assert document["housing_preferences"]["ubicacion_deseada"] == "Chía"
    assert (tmp_path / "latest_profile.json").exists()
