"""Persistence abstractions."""

from app.repositories.json_project_repository import JsonProjectRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.memory_lead_repository import MemoryLeadRepository
from app.repositories.project_repository import ProjectRepository

__all__ = [
    "JsonProjectRepository",
    "LeadRepository",
    "MemoryLeadRepository",
    "ProjectRepository",
]
