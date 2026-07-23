"""Build historical project profiles and matching report from processed data.

Usage:
    python scripts/build_project_profiles.py \
      --buyers data/processed/buyers_clean.csv \
      --projects data/processed/projects_catalog.json \
      --output data/processed/project_profiles.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.project_profile_builder import (  # noqa: E402
    build_profile_for_group,
    match_catalog_to_history,
)
from app.utils.normalization import strip_text  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Construye perfiles históricos por proyecto sin modificar fuentes.",
    )
    parser.add_argument("--buyers", type=str, required=True, help="CSV o JSON de buyers_clean")
    parser.add_argument("--projects", type=str, required=True, help="JSON del catálogo")
    parser.add_argument(
        "--output",
        type=str,
        default="data/processed/project_profiles.json",
        help="Ruta de salida de perfiles",
    )
    parser.add_argument(
        "--matching-report",
        type=str,
        default="data/processed/project_matching_report.json",
        help="Ruta del reporte de coincidencias",
    )
    return parser.parse_args()


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def load_buyers(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".json":
        return pd.read_json(path)
    return pd.read_csv(path)


def main() -> int:
    _configure_stdout()
    args = parse_args()
    buyers_path = Path(args.buyers)
    projects_path = Path(args.projects)
    output_path = Path(args.output)
    report_path = Path(args.matching_report)

    if not buyers_path.exists():
        print(f"No existe buyers: {buyers_path}")
        return 1
    if not projects_path.exists():
        print(f"No existe catálogo: {projects_path}")
        return 1

    buyers = load_buyers(buyers_path)
    catalog = json.loads(projects_path.read_text(encoding="utf-8"))
    if "nombre_proyecto" not in buyers.columns:
        print("El archivo de compradores no contiene la columna 'nombre_proyecto'.")
        return 1

    history_names = sorted(
        {
            strip_text(name) or ""
            for name in buyers["nombre_proyecto"].dropna().astype(str).tolist()
            if strip_text(name)
        }
    )
    catalog_names = [
        strip_text(item.get("nombre")) or ""
        for item in catalog
        if strip_text(item.get("nombre"))
    ]

    matching = match_catalog_to_history(catalog_names, history_names)
    name_links = {
        item["catalog_name"]: item["history_name"]
        for item in matching["matched"] + matching["approximate"]
    }

    profiles = []
    for project in catalog:
        catalog_name = strip_text(project.get("nombre")) or "Proyecto sin nombre"
        history_name = name_links.get(catalog_name)
        if history_name is None:
            profile = {
                "project_id": project.get("id"),
                "catalog_name": catalog_name,
                "history_name": None,
                "match_kind": None,
                "total_buyers": 0,
                "affiliated_percentage": None,
                "non_affiliated_percentage": None,
                "category_distribution": {},
                "salary_range_distribution": {},
                "segments": {},
                "dependents_distribution": {},
                "dependents_average": None,
                "household_composition_distribution": {},
                "frequent_locations": [],
                "frequent_financial_entities": [],
                "frequent_companies": [],
                "enterprise_pyramid_distribution": {},
                "historical_price_min": None,
                "historical_price_max": None,
                "historical_price_median": None,
                "historical_price_reliable": False,
                "withdrawal_percentage": None,
                "missing_data_percentage": {},
                "age_range_distribution": {},
                "notes": ["Sin compradores históricos emparejados de forma confiable."],
            }
        else:
            group = buyers[buyers["nombre_proyecto"].astype(str).str.strip() == history_name]
            profile = build_profile_for_group(group, history_name)
            profile["project_id"] = project.get("id")
            profile["catalog_name"] = catalog_name
            profile["history_name"] = history_name
            match_meta = next(
                (
                    item
                    for item in matching["matched"] + matching["approximate"]
                    if item["catalog_name"] == catalog_name
                ),
                {"kind": "exact"},
            )
            profile["match_kind"] = match_meta.get("kind")
        profile["brochure_url"] = project.get("brochure_url")
        profile["recorrido_360_url"] = project.get("recorrido_360_url")
        profile["disponible"] = project.get("disponible", True)
        profile["municipio"] = project.get("municipio")
        profile["departamento"] = project.get("departamento")
        profile["ubicacion"] = project.get("ubicacion")
        profile["etapa"] = project.get("etapa")
        profile["valor_minimo_catalogo"] = project.get("valor_minimo")
        profile["valor_maximo_catalogo"] = project.get("valor_maximo")
        profiles.append(profile)

    history_only = []
    for history_name in matching["history_without_catalog"]:
        group = buyers[buyers["nombre_proyecto"].astype(str).str.strip() == history_name]
        item = build_profile_for_group(group, history_name)
        item["project_id"] = None
        item["catalog_name"] = None
        item["history_name"] = history_name
        item["match_kind"] = "history_only"
        history_only.append(item)

    output_payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "sources": {
            "buyers": str(buyers_path),
            "projects": str(projects_path),
        },
        "catalog_profiles": profiles,
        "history_only_profiles": history_only,
        "limitations": [
            "La base contiene compradores históricos y desistimientos, no todos los leads.",
            "municipio/departamento/ubicacion del catálogo pueden estar vacíos.",
            "Los valores históricos de vivienda pueden tener escala no confiable.",
            "No se usa género, edad o estrato para recomendaciones.",
        ],
    }

    report_payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        **matching,
        "summary": {
            "catalog_projects": len(catalog_names),
            "history_projects": len(history_names),
            "matched": len(matching["matched"]),
            "approximate": len(matching["approximate"]),
            "ambiguous": len(matching["ambiguous"]),
            "catalog_without_history": len(matching["catalog_without_history"]),
            "history_without_catalog": len(matching["history_without_catalog"]),
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_path.write_text(
        json.dumps(report_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Generado: {output_path}")
    print(f"Generado: {report_path}")
    print("Resumen matching:", report_payload["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
