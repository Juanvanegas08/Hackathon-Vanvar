"""JSON-backed project repository."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from app.core.config import Settings, get_settings
from app.models.project import HistoricalProfile, Project
from app.models.project_alias import CanonicalProject
from app.services.project_canonicalization_service import ProjectCanonicalizationService
from app.utils.project_matching import normalize_project_name


class JsonProjectRepository:
    """Load projects and historical profiles from processed JSON files."""

    def __init__(
        self,
        settings: Settings | None = None,
        catalog_path: str | Path | None = None,
        profiles_path: str | Path | None = None,
        canonical_path: str | Path | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._catalog_path = Path(catalog_path or self._settings.projects_catalog_path)
        self._profiles_path = Path(profiles_path or self._settings.project_profiles_path)
        self._canonical_path = Path(
            canonical_path or self._settings.projects_canonical_path
        )
        self._projects: list[Project] = []
        self._by_id: dict[UUID, Project] = {}
        self._profiles_loaded = False
        self._using_canonical = False
        self.reload()

    def reload(self) -> None:
        """Reload catalog and optional profiles from disk."""
        if self._canonical_path.exists():
            self._load_canonical()
            return

        catalog_items = self._read_json_list(self._catalog_path)
        profiles_by_id, profiles_by_name = self._load_profiles()
        projects: list[Project] = []
        for item in catalog_items:
            project = Project.model_validate(item)
            profile = profiles_by_id.get(str(project.id))
            if profile is None:
                profile = profiles_by_name.get(normalize_project_name(project.nombre) or "")
            if profile is not None:
                project = project.model_copy(update={"perfil_historico": profile})
            # Attach runtime canonical metadata for dedupe safety.
            service = ProjectCanonicalizationService(settings=self._settings)
            canonical_id, canonical_name, kind = service.resolve_canonical_id(project.nombre)
            project = project.model_copy(
                update={
                    "metadata": {
                        **project.metadata,
                        "canonical_project_id": canonical_id,
                        "canonical_name": canonical_name,
                        "canonical_match_kind": kind,
                        "aliases": [project.nombre],
                    }
                }
            )
            projects.append(project)

        self._projects = projects
        self._by_id = {project.id: project for project in projects}
        self._using_canonical = False

    def list_all(self) -> list[Project]:
        return list(self._projects)

    def get_by_id(self, project_id: UUID) -> Project | None:
        return self._by_id.get(project_id)

    def get_by_name(self, name: str) -> Project | None:
        target = normalize_project_name(name)
        if target is None:
            return None
        for project in self._projects:
            aliases = project.metadata.get("aliases", [])
            names = [project.nombre, *aliases]
            if any(normalize_project_name(str(item)) == target for item in names):
                return project
        return None

    def list_available(self) -> list[Project]:
        return [project for project in self._projects if project.disponible]

    def get_historical_profile(self, project_id: UUID) -> HistoricalProfile | None:
        project = self.get_by_id(project_id)
        if project is None:
            return None
        return project.perfil_historico

    def profiles_available(self) -> bool:
        return self._profiles_loaded

    def using_canonical_catalog(self) -> bool:
        return self._using_canonical

    def filter_projects(
        self,
        *,
        disponible: bool | None = None,
        municipio: str | None = None,
        departamento: str | None = None,
        nombre: str | None = None,
    ) -> list[Project]:
        """Apply optional listing filters."""
        results = self.list_all()
        if disponible is not None:
            results = [project for project in results if project.disponible is disponible]
        if municipio:
            needle = normalize_project_name(municipio)
            results = [
                project
                for project in results
                if normalize_project_name(project.municipio) == needle
            ]
        if departamento:
            needle = normalize_project_name(departamento)
            results = [
                project
                for project in results
                if normalize_project_name(project.departamento) == needle
            ]
        if nombre:
            needle = normalize_project_name(nombre) or ""
            filtered: list[Project] = []
            for project in results:
                aliases = [project.nombre, *project.metadata.get("aliases", [])]
                if any(needle in (normalize_project_name(str(item)) or "") for item in aliases):
                    filtered.append(project)
            results = filtered
        return results

    def _load_canonical(self) -> None:
        payload = json.loads(self._canonical_path.read_text(encoding="utf-8"))
        items = payload.get("projects", [])
        canonical_projects = [CanonicalProject.model_validate(item) for item in items]
        service = ProjectCanonicalizationService(settings=self._settings)
        self._projects = service.to_project_models(canonical_projects)
        self._by_id = {project.id: project for project in self._projects}
        self._profiles_loaded = any(
            project.perfil_historico.total_buyers > 0 for project in self._projects
        )
        self._using_canonical = True

    def _load_profiles(
        self,
    ) -> tuple[dict[str, HistoricalProfile], dict[str, HistoricalProfile]]:
        if not self._profiles_path.exists():
            self._profiles_loaded = False
            return {}, {}

        payload = json.loads(self._profiles_path.read_text(encoding="utf-8"))
        catalog_profiles = payload.get("catalog_profiles", [])
        by_id: dict[str, HistoricalProfile] = {}
        by_name: dict[str, HistoricalProfile] = {}
        for item in catalog_profiles:
            profile = HistoricalProfile(
                total_buyers=int(item.get("total_buyers") or 0),
                affiliated_percentage=item.get("affiliated_percentage"),
                non_affiliated_percentage=item.get("non_affiliated_percentage"),
                category_distribution=item.get("category_distribution") or {},
                salary_range_distribution=item.get("salary_range_distribution") or {},
                segments=item.get("segments") or {},
                dependents_distribution=item.get("dependents_distribution") or {},
                dependents_average=item.get("dependents_average"),
                household_composition_distribution=(
                    item.get("household_composition_distribution") or {}
                ),
                frequent_locations=item.get("frequent_locations") or [],
                frequent_financial_entities=item.get("frequent_financial_entities") or [],
                frequent_companies=item.get("frequent_companies") or [],
                enterprise_pyramid_distribution=(
                    item.get("enterprise_pyramid_distribution") or {}
                ),
                historical_price_min=item.get("historical_price_min"),
                historical_price_max=item.get("historical_price_max"),
                historical_price_median=item.get("historical_price_median"),
                historical_price_reliable=bool(item.get("historical_price_reliable", False)),
                withdrawal_percentage=item.get("withdrawal_percentage"),
                missing_data_percentage=item.get("missing_data_percentage") or {},
                age_range_distribution=item.get("age_range_distribution") or {},
            )
            project_id = item.get("project_id")
            if project_id:
                by_id[str(project_id)] = profile
            catalog_name = item.get("catalog_name")
            if catalog_name:
                key = normalize_project_name(catalog_name)
                if key:
                    by_name[key] = profile

        self._profiles_loaded = bool(catalog_profiles)
        return by_id, by_name

    @staticmethod
    def _read_json_list(path: Path) -> list[dict[str, object]]:
        if not path.exists():
            return []
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return payload
        return []
