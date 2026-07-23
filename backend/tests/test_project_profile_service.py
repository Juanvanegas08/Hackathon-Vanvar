"""Tests for historical project profiles and matching."""

import json
from pathlib import Path

import pandas as pd
from app.repositories.json_project_repository import JsonProjectRepository
from app.services.project_profile_builder import (
    build_profile_for_group,
    match_catalog_to_history,
)
from app.services.project_profile_service import ProjectProfileService
from app.utils.project_matching import compare_project_names


def test_build_profile_handles_missing_columns() -> None:
    df = pd.DataFrame({"nombre_proyecto": ["Alpha", "Alpha"]})
    profile = build_profile_for_group(df, "Alpha")
    assert profile["total_buyers"] == 2
    assert profile["category_distribution"] == {}
    assert profile["segments"] == {}
    assert profile["affiliated_percentage"] is None


def test_affiliation_and_category_not_mixed_with_segment() -> None:
    df = pd.DataFrame(
        {
            "nombre_proyecto": ["Alpha", "Alpha", "Alpha"],
            "afiliado_normalizado": [True, True, False],
            "categoria": ["A", "A", "B"],
            "segmento_poblacional": ["Básico", "Medio", "Joven"],
        }
    )
    profile = build_profile_for_group(df, "Alpha")
    assert profile["affiliated_percentage"] == 66.67
    assert "A" in profile["category_distribution"]
    assert "Básico" in profile["segments"]
    assert "A" not in profile["segments"]
    assert "Básico" not in profile["category_distribution"]


def test_small_sample_does_not_fail() -> None:
    df = pd.DataFrame(
        {
            "nombre_proyecto": ["Solo"],
            "afiliado_normalizado": [True],
            "categoria": ["C"],
        }
    )
    profile = build_profile_for_group(df, "Solo")
    assert profile["total_buyers"] == 1
    assert profile["category_distribution"]["C"] == 100.0


def test_matching_report_structure() -> None:
    catalog = ["MONGUI", "LA MACARENA", "REVISTA"]
    history = [
        "Agrupación De Vivienda Monguí",
        "Agrupación De Vivienda La Macarena",
        "Proyecto Sin Catalogo",
    ]
    report = match_catalog_to_history(catalog, history)
    assert "matched" in report or "approximate" in report
    assert "ambiguous" in report
    assert "catalog_without_history" in report
    assert "history_without_catalog" in report
    assert "Proyecto Sin Catalogo" in report["history_without_catalog"]


def test_exact_and_approximate_name_matching() -> None:
    exact = compare_project_names("ABETO", "ABETO")
    assert exact.kind == "exact"
    approx = compare_project_names("MONGUI", "Agrupación De Vivienda Monguí")
    assert approx.kind in {"exact", "approximate"}


def test_repository_loads_profiles_without_mutating_source(
    tmp_path: Path,
) -> None:
    catalog = [
        {
            "id": "00000000-0000-0000-0000-000000000101",
            "nombre": "Alpha",
            "disponible": True,
            "perfil_historico": {},
            "metadata": {},
        }
    ]
    profiles = {
        "catalog_profiles": [
            {
                "project_id": "00000000-0000-0000-0000-000000000101",
                "catalog_name": "Alpha",
                "total_buyers": 12,
                "affiliated_percentage": 80.0,
                "non_affiliated_percentage": 20.0,
                "category_distribution": {"A": 70.0},
                "salary_range_distribution": {"Entre 1 y 1.5 SMLV": 60.0},
                "segments": {"Básico": 55.0},
                "historical_price_reliable": False,
            }
        ]
    }
    catalog_path = tmp_path / "catalog.json"
    profiles_path = tmp_path / "profiles.json"
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    profiles_path.write_text(json.dumps(profiles), encoding="utf-8")
    original = catalog_path.read_text(encoding="utf-8")

    repo = JsonProjectRepository(
        catalog_path=catalog_path,
        profiles_path=profiles_path,
        canonical_path=tmp_path / "missing_canonical.json",
    )
    service = ProjectProfileService(repository=repo)
    assert service.profiles_ready() is True
    project = service.list_projects()[0]
    assert project.perfil_historico.total_buyers == 12
    assert project.perfil_historico.affiliated_percentage == 80.0
    assert catalog_path.read_text(encoding="utf-8") == original
