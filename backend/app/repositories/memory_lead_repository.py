"""In-memory lead repository for the first hackathon phase."""

from threading import Lock
from uuid import UUID

from app.core.exceptions import NotFoundError
from app.models.lead import Lead
from app.utils.identity_hash import normalize_document_number


class MemoryLeadRepository:
    """Thread-safe in-memory implementation of LeadRepository."""

    def __init__(self) -> None:
        self._leads: dict[UUID, Lead] = {}
        self._by_document: dict[tuple[str, str], UUID] = {}
        self._lock = Lock()

    def create(self, lead: Lead) -> Lead:
        with self._lock:
            self._leads[lead.id] = lead
            self._index_document(lead)
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
            self._index_document(lead)
            return lead

    def delete(self, lead_id: UUID) -> bool:
        with self._lock:
            lead = self._leads.pop(lead_id, None)
            if lead is None:
                return False
            key = self._document_key(lead)
            if key and self._by_document.get(key) == lead_id:
                self._by_document.pop(key, None)
            return True

    def get_by_document(
        self,
        document_type: str,
        document_number: str,
        *,
        country_code: str = "CO",
    ) -> Lead | None:
        _ = country_code
        key = (
            document_type.strip().upper(),
            normalize_document_number(document_number),
        )
        with self._lock:
            lead_id = self._by_document.get(key)
            if lead_id is None:
                return None
            return self._leads.get(lead_id)

    def save_profile(self, lead: Lead) -> Lead:
        if self.get_by_id(lead.id) is None:
            return self.create(lead)
        return self.update(lead)

    def reset_profile(self, lead: Lead) -> Lead:
        """Replace the stored lead with a wiped profile (memory has no recs table)."""
        return self.save_profile(lead)

    def clear(self) -> None:
        """Remove all leads (intended for tests)."""
        with self._lock:
            self._leads.clear()
            self._by_document.clear()

    def _index_document(self, lead: Lead) -> None:
        key = self._document_key(lead)
        if key is not None:
            self._by_document[key] = lead.id

    @staticmethod
    def _document_key(lead: Lead) -> tuple[str, str] | None:
        if not lead.document_type or not lead.document_number:
            return None
        doc_type = (
            lead.document_type.value
            if hasattr(lead.document_type, "value")
            else str(lead.document_type)
        )
        return doc_type.upper(), normalize_document_number(lead.document_number)
