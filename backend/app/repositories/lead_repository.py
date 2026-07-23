"""Lead repository protocol for swappable persistence backends."""

from typing import Protocol
from uuid import UUID

from app.models.lead import Lead


class LeadRepository(Protocol):
    """Persistence contract for lead profiles."""

    def create(self, lead: Lead) -> Lead:
        """Persist a new lead."""

    def get_by_id(self, lead_id: UUID) -> Lead | None:
        """Return a lead by ID or None if missing."""

    def list_all(self) -> list[Lead]:
        """Return all stored leads."""

    def update(self, lead: Lead) -> Lead:
        """Replace an existing lead document."""

    def delete(self, lead_id: UUID) -> bool:
        """Delete a lead. Returns True if a record was removed."""

    def get_by_document(
        self,
        document_type: str,
        document_number: str,
        *,
        country_code: str = "CO",
    ) -> Lead | None:
        """Return an existing lead matched by document identifier."""

    def save_profile(self, lead: Lead) -> Lead:
        """Persist the completed/updated profile for a lead."""
