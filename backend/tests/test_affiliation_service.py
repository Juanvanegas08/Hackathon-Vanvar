"""Tests for affiliation category calculation."""

import pytest
from app.core.config import Settings
from app.core.exceptions import InvalidSmmlvError, ValidationBusinessError
from app.models.lead import AffiliationCategory, Lead
from app.schemas.lead import LeadCreate
from app.services.affiliation_service import AffiliationService
from pydantic import ValidationError


@pytest.fixture
def service() -> AffiliationService:
    return AffiliationService(Settings(SMMLV=1_000_000))


def test_affiliated_exactly_2_smmlv_is_a(service: AffiliationService) -> None:
    result = service.calculate_category(afiliado=True, salario_mensual=2_000_000)
    assert result.categoria == AffiliationCategory.A
    assert float(result.salario_en_smmlv or 0) == 2.0


def test_affiliated_exactly_4_smmlv_is_b(service: AffiliationService) -> None:
    result = service.calculate_category(afiliado=True, salario_mensual=4_000_000)
    assert result.categoria == AffiliationCategory.B
    assert float(result.salario_en_smmlv or 0) == 4.0


def test_affiliated_above_4_smmlv_is_c(service: AffiliationService) -> None:
    result = service.calculate_category(afiliado=True, salario_mensual=4_000_001)
    assert result.categoria == AffiliationCategory.C


def test_non_affiliated_is_d(service: AffiliationService) -> None:
    result = service.calculate_category(afiliado=False, salario_mensual=None)
    assert result.categoria == AffiliationCategory.D
    assert result.afiliado is False


def test_unknown_affiliation_has_no_category(service: AffiliationService) -> None:
    result = service.calculate_category(afiliado=None, salario_mensual=2_000_000)
    assert result.categoria is None
    assert result.fuente.value == "indeterminada"


def test_affiliated_without_salary_has_no_category(service: AffiliationService) -> None:
    result = service.calculate_category(afiliado=True, salario_mensual=None)
    assert result.categoria is None


def test_invalid_smmlv_raises_controlled_error() -> None:
    service = AffiliationService(Settings(SMMLV=0))
    with pytest.raises(InvalidSmmlvError):
        service.calculate_category(afiliado=True, salario_mensual=2_000_000)


def test_negative_salary_fails_validation(service: AffiliationService) -> None:
    with pytest.raises(ValidationBusinessError):
        service.calculate_category(afiliado=True, salario_mensual=-1)

    with pytest.raises(ValidationError):
        LeadCreate(salario_mensual=-100)

    with pytest.raises(ValidationError):
        Lead(salario_mensual=-50)


def test_requires_confirmation_when_not_confirmed(service: AffiliationService) -> None:
    result = service.calculate_category(
        afiliado=True,
        salario_mensual=1_500_000,
        afiliacion_confirmada=False,
    )
    assert result.requiere_confirmacion is True
