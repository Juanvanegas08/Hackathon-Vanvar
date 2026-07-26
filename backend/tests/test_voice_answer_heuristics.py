"""Tests for voice answer transcript heuristics."""

from app.services.voice_orchestration_service import VoiceOrchestrationService as V


def test_currency_hedge_is_not_treated_as_question() -> None:
    assert V._looks_like_user_question("no sé cuánto exacto pero como dos millones") is False
    assert V._looks_like_user_question("cuánto? dos millones") is True  # has ?
    assert V._looks_like_non_answer_transcript(
        "más o menos tres millones de pesos"
    ) is False


def test_clear_doubt_is_question() -> None:
    assert V._looks_like_user_question("tengo una duda sobre el subsidio") is True
    assert V._looks_like_user_question("qué significa VIS") is True
    assert V._looks_like_user_question("cuánto es el smmlv") is True


def test_plain_amount_is_answer() -> None:
    assert V._looks_like_user_question("dos millones") is False
    assert V._looks_like_non_answer_transcript("dos millones") is False
    assert V._looks_like_non_answer_transcript("sí") is False


def test_project_deferral_phrases() -> None:
    assert V._looks_like_project_deferral("lo que me recomiendes") is True
    assert V._looks_like_project_deferral("perdón, mejor lo que me recomiendes") is True
    assert V._looks_like_project_deferral("Proyecto Monguí") is False


def test_opening_mentions_duration() -> None:
    from app.models.lead import Lead

    opening = V._opening_message(Lead(nombre="Ana"), "Ana")
    assert "minuto" in opening.lower()
    assert "ahora" in opening.lower() or "tarde" in opening.lower() or "después" in opening.lower()
