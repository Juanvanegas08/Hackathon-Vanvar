"""Tests for readiness scoring."""

import inspect
import re

from app.models.evaluation import ConfidenceLevel
from app.models.lead import CreditSituation, Lead, LeadStatus, PurchaseTimeline
from app.services.readiness_service import ReadinessService


def test_empty_profile_has_low_score() -> None:
    service = ReadinessService()
    result = service.evaluate(Lead())
    assert result.readiness_score < 45
    assert result.status == LeadStatus.RUTA_NUTRICION
    assert result.confidence == ConfidenceLevel.LOW


def test_complete_profile_has_high_score() -> None:
    service = ReadinessService()
    lead = Lead(
        consentimiento=True,
        afiliado=True,
        afiliacion_confirmada=True,
        salario_mensual=2_500_000,
        ingreso_hogar=4_200_000,
        ahorro=18_000_000,
        obligaciones_mensuales=500_000,
        tiene_vivienda=False,
        personas_hogar=3,
        personas_a_cargo=1,
        situacion_crediticia=CreditSituation.AL_DIA,
        ubicacion_deseada="Bogotá",
        plazo_compra=PurchaseTimeline.TRES_MESES,
        proyecto_interes="Proyecto Centro",
    )
    result = service.evaluate(lead)
    assert result.readiness_score >= 75
    assert result.status == LeadStatus.LISTO_PARA_ASESOR


def test_non_affiliated_is_not_discarded() -> None:
    service = ReadinessService()
    lead = Lead(
        consentimiento=True,
        afiliado=False,
        salario_mensual=5_000_000,
        ingreso_hogar=7_000_000,
        ahorro=30_000_000,
        obligaciones_mensuales=800_000,
        tiene_vivienda=False,
        personas_hogar=2,
        situacion_crediticia=CreditSituation.AL_DIA,
        ubicacion_deseada="Cali",
        plazo_compra=PurchaseTimeline.SEIS_MESES,
    )
    result = service.evaluate(lead)
    assert result.status == LeadStatus.NO_AFILIADO_EN_EVALUACION
    assert result.status != LeadStatus.RUTA_NUTRICION or result.readiness_score >= 45


def test_missing_critical_data_reduces_confidence() -> None:
    service = ReadinessService()
    lead = Lead(
        consentimiento=True,
        afiliado=True,
        salario_mensual=None,
        ahorro=None,
        ubicacion_deseada="Bogotá",
    )
    result = service.evaluate(lead)
    assert result.confidence == ConfidenceLevel.LOW


def test_does_not_use_gender_age_or_stratum() -> None:
    source = inspect.getsource(ReadinessService).lower()
    # Avoid substring false positives (e.g. "age" inside "percentage").
    forbidden_patterns = [
        r"\bgenero\b",
        r"\bgénero\b",
        r"\bedad\b",
        r"\bestrato\b",
        r"\bgender\b",
        r"\bage\b",
        r"\bstratum\b",
    ]
    for pattern in forbidden_patterns:
        assert re.search(pattern, source) is None
