"""Build canonical project catalog from aliases, catalog and profiles.

Usage:
    python scripts/build_canonical_projects.py \
      --catalog data/processed/projects_catalog.json \
      --profiles data/processed/project_profiles.json \
      --aliases data/processed/project_aliases.json \
      --output data/processed/projects_canonical.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.project_canonicalization_service import (  # noqa: E402
    ProjectCanonicalizationService,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Consolida proyectos canónicos.")
    parser.add_argument("--catalog", default="data/processed/projects_catalog.json")
    parser.add_argument("--profiles", default="data/processed/project_profiles.json")
    parser.add_argument("--aliases", default="data/processed/project_aliases.json")
    parser.add_argument("--output", default="data/processed/projects_canonical.json")
    parser.add_argument(
        "--report",
        default="data/processed/project_canonicalization_report.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    catalog_path = Path(args.catalog)
    profiles_path = Path(args.profiles)
    aliases_path = Path(args.aliases)
    output_path = Path(args.output)
    report_path = Path(args.report)

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    profiles_payload = json.loads(profiles_path.read_text(encoding="utf-8"))
    profiles = profiles_payload.get("catalog_profiles", [])

    service = ProjectCanonicalizationService(aliases_path=aliases_path)
    projects, report = service.consolidate(catalog, profiles)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "sources": {
            "catalog": str(catalog_path),
            "profiles": str(profiles_path),
            "aliases": str(aliases_path),
        },
        "projects": [item.model_dump(mode="json") for item in projects],
    }
    report["generated_at"] = datetime.now(UTC).isoformat()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generado: {output_path}")
    print(f"Generado: {report_path}")
    print("Resumen:", report.get("summary"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
