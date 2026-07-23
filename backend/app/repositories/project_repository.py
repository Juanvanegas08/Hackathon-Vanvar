"""Project repository protocol."""

from typing import Protocol
from uuid import UUID

from app.models.project import HistoricalProfile, Project


class ProjectRepository(Protocol):
    """Persistence contract for housing projects."""

    def list_all(self) -> list[Project]:
        """Return all projects."""

    def get_by_id(self, project_id: UUID) -> Project | None:
        """Return a project by ID."""

    def get_by_name(self, name: str) -> Project | None:
        """Return a project by name (normalized match)."""

    def list_available(self) -> list[Project]:
        """Return projects marked as available."""

    def get_historical_profile(self, project_id: UUID) -> HistoricalProfile | None:
        """Return historical profile for a project."""

    def profiles_available(self) -> bool:
        """Return True when historical profiles were loaded."""
