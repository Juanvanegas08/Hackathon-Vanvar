"""Seed brochure / 360 URLs and locations onto existing housing.projects.

Uses projects_catalog.json produced by prepare_data --brochures.
Matches projects by name (does not require a full historical reseed).

Usage:
    python scripts/seed_brochure_assets.py
    python scripts/seed_brochure_assets.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings  # noqa: E402
from app.db.models.housing import Project, ProjectAlias, ProjectAsset, ProjectLocation  # noqa: E402
from app.utils.normalization import strip_text  # noqa: E402
from app.utils.project_matching import (  # noqa: E402
    compare_project_names,
    normalize_project_name,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Actualiza assets brochure/360 y ubicaciones desde projects_catalog.json",
    )
    parser.add_argument(
        "--projects",
        type=str,
        default="data/processed/projects_catalog.json",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def find_db_project(session: Session, catalog_name: str) -> Project | None:
    projects = list(session.scalars(select(Project)))
    best: tuple[float, Project] | None = None
    for project in projects:
        decision = compare_project_names(catalog_name, project.name)
        if decision.kind in {"exact", "approximate"}:
            if best is None or decision.score > best[0]:
                best = (decision.score, project)
    return best[1] if best else None


def upsert_asset(
    session: Session,
    *,
    project_id: UUID,
    asset_type: str,
    url: str,
    label: str,
    is_primary: bool,
) -> str:
    existing = session.scalar(
        select(ProjectAsset).where(
            ProjectAsset.project_id == project_id,
            ProjectAsset.asset_type == asset_type,
            ProjectAsset.url == url,
        )
    )
    if existing is not None:
        existing.label = label
        existing.is_primary = is_primary
        existing.is_active = True
        return "updated"
    session.add(
        ProjectAsset(
            project_id=project_id,
            asset_type=asset_type,
            url=url,
            label=label,
            is_primary=is_primary,
            is_active=True,
        )
    )
    return "inserted"


def upsert_location(
    session: Session,
    *,
    project_id: UUID,
    ubicacion: str,
) -> str:
    existing = session.scalar(
        select(ProjectLocation).where(
            ProjectLocation.project_id == project_id,
            ProjectLocation.source == "brochure",
            ProjectLocation.is_primary.is_(True),
        )
    )
    if existing is not None:
        existing.city = ubicacion
        existing.municipality = ubicacion
        existing.reliable = True
        return "updated"
    session.add(
        ProjectLocation(
            project_id=project_id,
            city=ubicacion,
            municipality=ubicacion,
            country_code="CO",
            is_primary=True,
            source="brochure",
            reliable=True,
        )
    )
    return "inserted"


def upsert_alias(
    session: Session,
    *,
    project_id: UUID,
    alias: str,
) -> str:
    normalized = normalize_project_name(alias) or alias.lower()
    existing = session.scalar(
        select(ProjectAlias).where(ProjectAlias.normalized_alias == normalized)
    )
    if existing is not None:
        existing.project_id = project_id
        existing.alias = alias
        existing.source = "brochure"
        existing.matching_method = "brochure_alias"
        return "updated"
    session.add(
        ProjectAlias(
            project_id=project_id,
            alias=alias,
            normalized_alias=normalized,
            source="brochure",
            matching_method="brochure_alias",
            confidence=None,
        )
    )
    return "inserted"


def main() -> int:
    _configure_stdout()
    args = parse_args()
    projects_path = Path(args.projects)
    if not projects_path.exists():
        print(f"No existe: {projects_path}")
        return 1

    catalog = json.loads(projects_path.read_text(encoding="utf-8"))
    if not isinstance(catalog, list):
        print("projects_catalog.json debe ser una lista.")
        return 1

    with_brochure = [
        item
        for item in catalog
        if item.get("brochure_url")
        or item.get("recorrido_360_url")
        or (item.get("recorridos_360") or [])
        or item.get("ubicacion")
    ]
    print(f"Proyectos en catálogo con brochure/360/ubicación: {len(with_brochure)}")

    if args.dry_run:
        for item in with_brochure:
            print(
                f"  - {item.get('nombre')}: brochure="
                f"{bool(item.get('brochure_url'))} 360="
                f"{bool(item.get('recorrido_360_url') or item.get('recorridos_360'))} "
                f"ubicacion={item.get('ubicacion')}"
            )
        print("Dry-run OK.")
        return 0

    settings = get_settings()
    url = settings.get_database_url()
    if not url:
        print("DATABASE_URL no está configurada.")
        return 1

    sync_url = url.replace("postgresql+psycopg://", "postgresql://", 1)
    engine = create_engine(
        sync_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 30},
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    stats = {
        "matched": 0,
        "unmatched": 0,
        "assets_inserted": 0,
        "assets_updated": 0,
        "locations_upserted": 0,
        "aliases_upserted": 0,
    }

    try:
        with SessionLocal() as session:
            for item in with_brochure:
                name = strip_text(item.get("nombre"))
                if not name:
                    continue
                project = find_db_project(session, name)
                if project is None:
                    # Brochure-only extras (MULTIPROYECTO / REVISTA): create project.
                    if (item.get("metadata") or {}).get("source") == "brochure_extra":
                        from app.utils.project_matching import normalize_project_name as npn

                        slug_base = npn(name) or "brochure"
                        slug = "_".join(slug_base.split())[:180]
                        existing_slug = session.scalar(
                            select(Project).where(Project.canonical_slug == slug)
                        )
                        if existing_slug is None:
                            project = Project(
                                canonical_slug=slug,
                                name=name,
                                available=True,
                                project_type="brochure_extra",
                                metadata_={
                                    "source": "brochure_extra",
                                    **(item.get("metadata") or {}),
                                },
                            )
                            session.add(project)
                            session.flush()
                        else:
                            project = existing_slug
                    else:
                        print(f"Sin match en DB: {name}")
                        stats["unmatched"] += 1
                        continue

                stats["matched"] += 1
                meta = dict(project.metadata_ or {})
                meta.update(
                    {
                        "brochure_alias": (item.get("metadata") or {}).get("brochure_alias"),
                        "brochure_match_kind": (item.get("metadata") or {}).get(
                            "brochure_match_kind"
                        ),
                        "brochure_status": (item.get("metadata") or {}).get(
                            "brochure_status"
                        ),
                        "recorridos_360": item.get("recorridos_360") or [],
                    }
                )
                if item.get("ubicacion"):
                    meta["ubicacion"] = item["ubicacion"]
                project.metadata_ = meta

                brochure_url = strip_text(item.get("brochure_url"))
                if brochure_url:
                    result = upsert_asset(
                        session,
                        project_id=project.id,
                        asset_type="brochure",
                        url=brochure_url,
                        label="Brochure",
                        is_primary=True,
                    )
                    stats["assets_inserted" if result == "inserted" else "assets_updated"] += 1

                tour_urls = list(
                    dict.fromkeys(
                        [
                            *(item.get("recorridos_360") or []),
                            *([item["recorrido_360_url"]] if item.get("recorrido_360_url") else []),
                        ]
                    )
                )
                for index, tour_url in enumerate(tour_urls):
                    cleaned = strip_text(tour_url)
                    if not cleaned:
                        continue
                    result = upsert_asset(
                        session,
                        project_id=project.id,
                        asset_type="tour_360",
                        url=cleaned,
                        label="Recorrido 360" if index == 0 else f"Recorrido 360 #{index + 1}",
                        is_primary=index == 0,
                    )
                    stats["assets_inserted" if result == "inserted" else "assets_updated"] += 1

                ubicacion = strip_text(item.get("ubicacion") or item.get("municipio"))
                if ubicacion:
                    upsert_location(session, project_id=project.id, ubicacion=ubicacion)
                    stats["locations_upserted"] += 1

                alias = strip_text((item.get("metadata") or {}).get("brochure_alias"))
                if alias and normalize_project_name(alias) != normalize_project_name(
                    project.name
                ):
                    upsert_alias(session, project_id=project.id, alias=alias)
                    stats["aliases_upserted"] += 1

            session.commit()
            print("Seed brochure/360 completado.")
            print(json.dumps(stats, ensure_ascii=False, indent=2))
            return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Seed brochure FALLÓ: {type(exc).__name__}: {exc}")
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
