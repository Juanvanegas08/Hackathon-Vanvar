"""Tests for demo-safe email sanitization."""

from __future__ import annotations

from app.models.lead import Lead
from app.utils.email import sanitize_optional_email
from app.utils.synthetic_persons import build_synthetic_person, person_uuid_for_row


def test_sanitize_rejects_reserved_local_domain() -> None:
    assert sanitize_optional_email("user@demo.casalista.local") is None
    assert sanitize_optional_email("ana@example.com") == "ana@example.com"


def test_lead_tolerates_seeded_local_email() -> None:
    lead = Lead(correo="persona.demo@demo.casalista.local")
    assert lead.correo is None


def test_synthetic_person_email_is_valid() -> None:
    draft = build_synthetic_person(
        row_number=1,
        person_id=str(person_uuid_for_row(1)),
        affiliated=True,
        dependents=1,
        age_range="20 - 35 años",
        segment="NU",
    )
    assert draft.email.endswith("@example.com")
    assert sanitize_optional_email(draft.email) == draft.email.lower()
