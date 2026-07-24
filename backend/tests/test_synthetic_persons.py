"""Tests for deterministic synthetic person generation."""

from __future__ import annotations

from app.providers.mock_affiliation_provider import MockAffiliationLookupProvider
from app.utils.synthetic_persons import (
    build_synthetic_person,
    document_number_for_row,
    draft_to_affiliate_record,
    person_uuid_for_row,
)


def test_document_number_reserved_range() -> None:
    assert document_number_for_row(0) == "9000000000"
    assert document_number_for_row(4141) == "9000004141"


def test_person_uuid_is_stable() -> None:
    assert person_uuid_for_row(12) == person_uuid_for_row(12)
    assert person_uuid_for_row(12) != person_uuid_for_row(13)


def test_build_synthetic_person_is_deterministic() -> None:
    first = build_synthetic_person(
        row_number=7,
        person_id=str(person_uuid_for_row(7)),
        affiliated=True,
        dependents=2,
        age_range="20 - 35 años",
        segment="KAPPA",
    )
    second = build_synthetic_person(
        row_number=7,
        person_id=str(person_uuid_for_row(7)),
        affiliated=True,
        dependents=2,
        age_range="20 - 35 años",
        segment="KAPPA",
    )
    assert first == second
    assert first.affiliation_category in {"A", "B", "C"}
    assert first.estimated_age is not None
    assert 20 <= first.estimated_age <= 35


def test_non_affiliated_gets_category_d() -> None:
    draft = build_synthetic_person(
        row_number=3,
        person_id=str(person_uuid_for_row(3)),
        affiliated=False,
        dependents=None,
        age_range=None,
        segment=None,
    )
    assert draft.affiliation_category == "D"
    assert draft.affiliated is False


def test_mock_provider_merges_historical(tmp_path) -> None:
    curated = tmp_path / "curated.json"
    historical = tmp_path / "historical.json"
    curated.write_text(
        '[{"document_number":"1000000001","document_type":"CC",'
        '"first_name":"Laura","last_name":"Demo","affiliated":true,'
        '"affiliation_category":"A"}]',
        encoding="utf-8",
    )
    draft = build_synthetic_person(
        row_number=0,
        person_id=str(person_uuid_for_row(0)),
        affiliated=True,
        dependents=1,
        age_range="20 a 35 años",
        segment="NU",
    )
    historical.write_text(
        f"[{__import__('json').dumps(draft_to_affiliate_record(draft))}]",
        encoding="utf-8",
    )
    provider = MockAffiliationLookupProvider(
        path=curated,
        historical_path=historical,
    )
    assert provider.lookup("CC", "1000000001") is not None
    assert provider.lookup("CC", draft.document_number) is not None
    assert len(provider.list_demo_identities()) == 2
