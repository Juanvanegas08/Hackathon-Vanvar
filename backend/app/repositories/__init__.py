"""Lead persistence abstractions."""

from app.repositories.lead_repository import LeadRepository
from app.repositories.memory_lead_repository import MemoryLeadRepository

__all__ = ["LeadRepository", "MemoryLeadRepository"]
