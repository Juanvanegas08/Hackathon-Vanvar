"""Tests for the next-question engine."""

from app.models.lead import CreditSituation, Lead, PurchaseTimeline
from app.services.question_service import QuestionService


def test_does_not_ask_completed_field() -> None:
    service = QuestionService()
    lead = Lead(consentimiento=True, afiliado=True)
    response = service.get_next_question(lead)
    assert response.completed is False
    assert response.next_question is not None
    assert response.next_question.field != "consentimiento"
    assert response.next_question.field != "afiliado"


def test_prioritizes_affiliation_after_consent() -> None:
    service = QuestionService()
    lead = Lead(consentimiento=True)
    response = service.get_next_question(lead)
    assert response.next_question is not None
    assert response.next_question.field == "afiliado"


def test_requests_personal_salary_after_affiliation() -> None:
    service = QuestionService()
    lead = Lead(consentimiento=True, afiliado=True)
    response = service.get_next_question(lead)
    assert response.next_question is not None
    assert response.next_question.field == "salario_mensual"


def test_completed_profile_returns_completed_true() -> None:
    service = QuestionService()
    lead = Lead(
        consentimiento=True,
        afiliado=True,
        salario_mensual=2_500_000,
        ingreso_hogar=4_000_000,
        ahorro=10_000_000,
        obligaciones_mensuales=400_000,
        tiene_vivienda=False,
        personas_hogar=3,
        personas_a_cargo=1,
        situacion_crediticia=CreditSituation.AL_DIA,
        ubicacion_deseada="Bogotá",
        plazo_compra=PurchaseTimeline.SEIS_MESES,
        proyecto_interes="Proyecto Norte",
    )
    response = service.get_next_question(lead)
    assert response.completed is True
    assert response.next_question is None
