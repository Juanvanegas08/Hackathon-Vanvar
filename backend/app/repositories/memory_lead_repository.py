"""In-memory lead repository for the first hackathon phase."""

from threading import Lock
from uuid import UUID

from app.core.exceptions import NotFoundError
from app.models.lead import Lead


class MemoryLeadRepository:
    """Thread-safe in-memory implementation of LeadRepository."""

    def __init__(self) -> None:
        self._leads: dict[UUID, Lead] = {}
        self._lock = Lock()

    def create(self, lead: Lead) -> Lead:
        with self._lock:
            self._leads[lead.id] = lead
            return lead

    def get_by_id(self, lead_id: UUID) -> Lead | None:
        with self._lock:
            return self._leads.get(lead_id)

    def list_all(self) -> list[Lead]:
        with self._lock:
            return list(self._leads.values())

    def update(self, lead: Lead) -> Lead:
        with self._lock:
            if lead.id not in self._leads:
                raise NotFoundError(f"Lead {lead.id} no encontrado")
            self._leads[lead.id] = lead
            return lead

    def delete(self, lead_id: UUID) -> bool:
        with self._lock:
            return self._leads.pop(lead_id, None) is not None

    def clear(self) -> None:
        """Remove all leads (intended for tests)."""
        with self._lock:
            self._leads.clear()
