"""Affiliation lookup provider contract."""

from datetime import date
from typing import Protocol

from pydantic import BaseModel


class MockAffiliateRecord(BaseModel):
    """Fictional affiliate record used only for demonstration."""

    document_number: str
    document_type: str = "CC"
    first_name: str
    last_name: str
    phone: str | None = None
    email: str | None = None
    affiliated: bool
    affiliation_confirmed: bool = False
    affiliation_category: str | None = None
    company: str | None = None
    reported_salary: float | None = None
    salary_range: str | None = None
    dependents: int | None = None
    beneficiaries_registered: int | None = None
    segment: str | None = None
    source: str = "mock_affiliation_service"
    scenario: str | None = None
    last_updated_at: date | None = None


class AffiliationLookupProvider(Protocol):
    """Contract for affiliation/identity lookup backends."""

    def lookup(
        self,
        document_type: str,
        document_number: str,
    ) -> MockAffiliateRecord | None:
        """Return a matching record or None when unknown."""

    def list_demo_identities(self) -> list[MockAffiliateRecord]:
        """Return demo identities for development tooling."""
