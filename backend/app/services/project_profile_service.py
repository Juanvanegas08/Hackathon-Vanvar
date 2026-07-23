"""Helpers around historical project profiles."""

from pathlib import Path

from app.core.config import Settings, get_settings
from app.models.project import HistoricalProfile, Project
from app.repositories.json_project_repository import JsonProjectRepository
from app.repositories.project_repository import ProjectRepository


class ProjectProfileService:
    """Access project catalog and historical profiles."""

    def __init__(
        self,
        repository: ProjectRepository | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._repository = repository or JsonProjectRepository(self._settings)

    @property
    def repository(self) -> ProjectRepository:
        return self._repository

    def list_projects(
        self,
        *,
        disponible: bool | None = None,
        municipio: str | None = None,
        departamento: str | None = None,
        nombre: str | None = None,
    ) -> list[Project]:
        repo = self._repository
        if isinstance(repo, JsonProjectRepository):
            return repo.filter_projects(
                disponible=disponible,
                municipio=municipio,
                departamento=departamento,
                nombre=nombre,
            )
        projects = repo.list_all()
        if disponible is not None:
            projects = [item for item in projects if item.disponible is disponible]
        return projects

    def get_project(self, project_id: object) -> Project | None:
        from uuid import UUID

        return self._repository.get_by_id(UUID(str(project_id)))

    def get_profile(self, project_id: object) -> HistoricalProfile | None:
        from uuid import UUID

        return self._repository.get_historical_profile(UUID(str(project_id)))

    def profiles_ready(self) -> bool:
        return self._repository.profiles_available()

    def profiles_path_exists(self) -> bool:
        return Path(self._settings.project_profiles_path).exists()
