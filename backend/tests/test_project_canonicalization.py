"""Tests for canonical project consolidation and deduplicated recommendations."""

import json
from pathlib import Path
from uuid import uuid4

from app.core.config import Settings
from app.models.lead import Lead
from app.models.project import HistoricalProfile, Project
from app.services.project_canonicalization_service import ProjectCanonicalizationService
from app.services.recommendation_service import RecommendationService


def test_mongui_aliases_consolidate(tmp_path: Path) -> None:
    aliases = {
        "mongui": {
            "canonical_name": "Monguí",
            "aliases": ["Agrupación De Vivienda Monguí", "MONGUI", "Monguí / brochure"],
        }
    }
    aliases_path = tmp_path / "aliases.json"
    aliases_path.write_text(json.dumps(aliases), encoding="utf-8")
    service = ProjectCanonicalizationService(aliases_path=aliases_path)
    catalog = [
        {"id": str(uuid4()), "nombre": "Agrupación De Vivienda Monguí", "disponible": True},
        {
            "id": str(uuid4()),
            "nombre": "MONGUI",
            "disponible": True,
            "brochure_url": "https://example.com/mongui",
        },
    ]
    profiles = [
        {
            "project_id": catalog[0]["id"],
            "catalog_name": catalog[0]["nombre"],
            "total_buyers": 50,
            "affiliated_percentage": 90.0,
            "historical_price_reliable": False,
        }
    ]
    projects, report = service.consolidate(catalog, profiles)
    mongui = next(item for item in projects if item.canonical_project_id == "mongui")
    assert mongui.name == "Monguí"
    assert "MONGUI" in mongui.aliases
    assert mongui.brochure_url == "https://example.com/mongui"
    assert mongui.historical_profile.total_buyers == 50
    assert any(item["nombre"] == "Agrupación De Vivienda Monguí" for item in mongui.catalog_records)
    assert report["summary"]["canonical_projects"] == 1


def test_ambiguous_matches_are_not_auto_merged(tmp_path: Path) -> None:
    aliases_path = tmp_path / "aliases.json"
    aliases_path.write_text("{}", encoding="utf-8")
    service = ProjectCanonicalizationService(aliases_path=aliases_path)
    catalog = [
        {"id": str(uuid4()), "nombre": "Reserva Del Nogal", "disponible": True},
        {"id": str(uuid4()), "nombre": "Los Nogales", "disponible": True},
    ]
    projects, report = service.consolidate(catalog, [])
    assert len(projects) == 2
    assert isinstance(report["pending_review"], list) or isinstance(
        report["ambiguous_candidates"], list
    )


def test_recommendations_dedupe_canonical_projects() -> None:
    shared_meta = {
        "canonical_project_id": "mongui",
        "canonical_name": "Monguí",
        "aliases": ["Agrupación De Vivienda Monguí", "MONGUI"],
    }
    projects = [
        Project(
            id=uuid4(),
            nombre="Agrupación De Vivienda Monguí",
            ubicacion="Monguí",
            disponible=True,
            perfil_historico=HistoricalProfile(
                total_buyers=80,
                affiliated_percentage=90.0,
                salary_range_distribution={"Entre 1 y 1.5 SMLV": 70.0},
            ),
            metadata=shared_meta,
        ),
        Project(
            id=uuid4(),
            nombre="MONGUI",
            ubicacion="Monguí",
            disponible=True,
            brochure_url="https://example.com/b",
            perfil_historico=HistoricalProfile(total_buyers=0),
            metadata=shared_meta,
        ),
    ]

    class Repo:
        def list_all(self) -> list[Project]:
            return projects

        def profiles_available(self) -> bool:
            return True

        def get_by_id(self, project_id: object) -> Project | None:
            return None

        def get_by_name(self, name: str) -> Project | None:
            return None

        def list_available(self) -> list[Project]:
            return projects

        def get_historical_profile(self, project_id: object) -> HistoricalProfile | None:
            return None

    service = RecommendationService(
        project_repository=Repo(),  # type: ignore[arg-type]
        settings=Settings(SMMLV=1_000_000),
    )
    lead = Lead(afiliado=True, salario_mensual=1_200_000, ubicacion_deseada="Monguí")
    first = service.recommend_for_lead(lead, limit=3)
    second = service.recommend_for_lead(lead, limit=3)
    ids = [item.canonical_project_id for item in first.recommended_projects]
    assert ids.count("mongui") == 1
    assert first.recommended_projects[0].project_name == "Monguí"
    assert 0 <= first.recommended_projects[0].compatibility_score <= 100
    assert first.model_dump(exclude={"generated_at"}) == second.model_dump(
        exclude={"generated_at"}
    )
