"""Seed historical housing data into PostgreSQL.

Loads processed artifacts produced by prepare_data / generate_synthetic_persons
/ build_project_profiles:

- projects_catalog.json → housing.projects (+ stages, prices, assets)
- persons_seed.json → identity.persons (+ identifiers, contacts) + affiliation
- buyers_seed.json → ingestion.import_batches + normalized_buyer_records (con person_id)
- project_profiles.json → housing.project_historical_profiles + distributions

Usage:
    python scripts/seed_historical_data.py
    python scripts/seed_historical_data.py --dry-run
    python scripts/seed_historical_data.py --force
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import create_engine, delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings  # noqa: E402
from app.db.models.affiliation import (  # noqa: E402
    AffiliationEmployer,
    AffiliationRecord,
)
from app.db.models.core import DataSource  # noqa: E402
from app.db.models.housing import (  # noqa: E402
    Project,
    ProjectAsset,
    ProjectHistoricalProfile,
    ProjectPrice,
    ProjectProfileDistribution,
    ProjectStage,
)
from app.db.models.identity import ContactPoint, Person, PersonIdentifier  # noqa: E402
from app.db.models.ingestion import (  # noqa: E402
    ImportBatch,
    NormalizedBuyerRecord,
    SeedExecution,
)
from app.utils.normalization import strip_text  # noqa: E402
from app.utils.project_matching import normalize_project_name  # noqa: E402
from app.utils.synthetic_persons import (  # noqa: E402
    affiliated_from_buyer_record,
    build_synthetic_person,
    draft_to_person_seed,
    person_uuid_for_row,
)

SEED_NAME = "hackathon_historical_buyers"
SEED_VERSION = "1.1.0"
DATA_SOURCE_CODE = "hackathon_buyers_export"
CHUNK_SIZE = 1000

DISTRIBUTION_FIELDS: tuple[tuple[str, str], ...] = (
    ("category_distribution", "category"),
    ("segments", "segment"),
    ("salary_range_distribution", "salary_range"),
    ("dependents_distribution", "dependents"),
    ("household_composition_distribution", "household_composition"),
    ("enterprise_pyramid_distribution", "enterprise_pyramid"),
    ("age_range_distribution", "age_range"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Carga artefactos históricos del reto Vivienda en PostgreSQL.",
    )
    parser.add_argument(
        "--buyers-seed",
        type=str,
        default="data/processed/buyers_seed.json",
        help="JSON de buyers_seed (default: data/processed/buyers_seed.json)",
    )
    parser.add_argument(
        "--projects",
        type=str,
        default="data/processed/projects_catalog.json",
        help="JSON del catálogo de proyectos",
    )
    parser.add_argument(
        "--profiles",
        type=str,
        default="data/processed/project_profiles.json",
        help="JSON de perfiles históricos",
    )
    parser.add_argument(
        "--persons-seed",
        type=str,
        default="data/processed/persons_seed.json",
        help="JSON de personas sintéticas (default: data/processed/persons_seed.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Valida archivos y plan sin escribir en la base",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reemplaza un seed previo con el mismo nombre/versión",
    )
    return parser.parse_args()


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def slugify_project(value: str) -> str:
    normalized = normalize_project_name(value) or "proyecto"
    tokens = [token for token in normalized.split(" ") if token]
    return "_".join(tokens)[:180] or "proyecto"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def combined_checksum(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_sha256(path).encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_optional_date(value: Any) -> date | None:
    text = strip_text(value)
    if text is None:
        return None
    return date.fromisoformat(text[:10])


def parse_optional_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, float) and value != value:  # NaN
        return None
    return Decimal(str(value))


def parse_optional_uuid(value: Any) -> UUID | None:
    text = strip_text(value)
    if text is None:
        return None
    return UUID(text)


def ensure_data_source(session: Session) -> DataSource:
    existing = session.scalar(
        select(DataSource).where(DataSource.code == DATA_SOURCE_CODE)
    )
    if existing is not None:
        return existing
    source = DataSource(
        code=DATA_SOURCE_CODE,
        name="Hackathon buyers export",
        description=(
            "Base anonimizada de compradores históricos del Reto Vivienda "
            "(Colsubsidio x 30X)."
        ),
        trust_level=80,
        is_official=True,
        is_active=True,
    )
    session.add(source)
    session.flush()
    return source


def find_seed_by_checksum(session: Session, checksum: str) -> SeedExecution | None:
    return session.scalar(
        select(SeedExecution).where(
            SeedExecution.seed_name == SEED_NAME,
            SeedExecution.seed_version == SEED_VERSION,
            SeedExecution.checksum == checksum,
        )
    )


def find_seeds_by_name_version(session: Session) -> list[SeedExecution]:
    return list(
        session.scalars(
            select(SeedExecution).where(
                SeedExecution.seed_name == SEED_NAME,
                SeedExecution.seed_version == SEED_VERSION,
            )
        )
    )


def find_seeds_by_name(session: Session) -> list[SeedExecution]:
    """All executions for this seed name (any version), for --force cleanup."""
    return list(
        session.scalars(
            select(SeedExecution).where(SeedExecution.seed_name == SEED_NAME)
        )
    )


def purge_previous_seed(session: Session, previous: SeedExecution) -> dict[str, int]:
    """Delete data linked to a previous seed execution via its import batch."""
    meta = previous.metadata_ or {}
    batch_id_raw = meta.get("import_batch_id")
    project_ids_raw = meta.get("project_ids") or []
    person_ids_raw = meta.get("person_ids") or []
    deleted = {
        "normalized_buyer_records": 0,
        "affiliation_employers": 0,
        "affiliation_records": 0,
        "person_identifiers": 0,
        "contact_points": 0,
        "persons": 0,
        "project_profile_distributions": 0,
        "project_historical_profiles": 0,
        "project_prices": 0,
        "project_assets": 0,
        "project_stages": 0,
        "projects": 0,
        "import_batches": 0,
        "seed_executions": 0,
    }

    if batch_id_raw:
        batch_id = UUID(str(batch_id_raw))
        deleted["normalized_buyer_records"] = session.execute(
            delete(NormalizedBuyerRecord).where(
                NormalizedBuyerRecord.batch_id == batch_id
            )
        ).rowcount or 0
        profile_ids = list(
            session.scalars(
                select(ProjectHistoricalProfile.id).where(
                    ProjectHistoricalProfile.source_batch_id == batch_id
                )
            )
        )
        if profile_ids:
            deleted["project_profile_distributions"] = session.execute(
                delete(ProjectProfileDistribution).where(
                    ProjectProfileDistribution.historical_profile_id.in_(profile_ids)
                )
            ).rowcount or 0
            deleted["project_historical_profiles"] = session.execute(
                delete(ProjectHistoricalProfile).where(
                    ProjectHistoricalProfile.id.in_(profile_ids)
                )
            ).rowcount or 0
        deleted["import_batches"] = session.execute(
            delete(ImportBatch).where(ImportBatch.id == batch_id)
        ).rowcount or 0

    person_ids = [UUID(str(item)) for item in person_ids_raw]
    if person_ids:
        affiliation_ids = list(
            session.scalars(
                select(AffiliationRecord.id).where(
                    AffiliationRecord.person_id.in_(person_ids)
                )
            )
        )
        if affiliation_ids:
            deleted["affiliation_employers"] = session.execute(
                delete(AffiliationEmployer).where(
                    AffiliationEmployer.affiliation_record_id.in_(affiliation_ids)
                )
            ).rowcount or 0
            deleted["affiliation_records"] = session.execute(
                delete(AffiliationRecord).where(
                    AffiliationRecord.id.in_(affiliation_ids)
                )
            ).rowcount or 0
        deleted["person_identifiers"] = session.execute(
            delete(PersonIdentifier).where(PersonIdentifier.person_id.in_(person_ids))
        ).rowcount or 0
        deleted["contact_points"] = session.execute(
            delete(ContactPoint).where(ContactPoint.person_id.in_(person_ids))
        ).rowcount or 0
        deleted["persons"] = session.execute(
            delete(Person).where(Person.id.in_(person_ids))
        ).rowcount or 0

    project_ids = [UUID(str(item)) for item in project_ids_raw]
    if project_ids:
        deleted["project_prices"] = session.execute(
            delete(ProjectPrice).where(ProjectPrice.project_id.in_(project_ids))
        ).rowcount or 0
        deleted["project_assets"] = session.execute(
            delete(ProjectAsset).where(ProjectAsset.project_id.in_(project_ids))
        ).rowcount or 0
        deleted["project_stages"] = session.execute(
            delete(ProjectStage).where(ProjectStage.project_id.in_(project_ids))
        ).rowcount or 0
        # Profiles not tied to batch (safety).
        orphan_profiles = list(
            session.scalars(
                select(ProjectHistoricalProfile.id).where(
                    ProjectHistoricalProfile.project_id.in_(project_ids)
                )
            )
        )
        if orphan_profiles:
            deleted["project_profile_distributions"] += session.execute(
                delete(ProjectProfileDistribution).where(
                    ProjectProfileDistribution.historical_profile_id.in_(orphan_profiles)
                )
            ).rowcount or 0
            deleted["project_historical_profiles"] += session.execute(
                delete(ProjectHistoricalProfile).where(
                    ProjectHistoricalProfile.id.in_(orphan_profiles)
                )
            ).rowcount or 0
        deleted["projects"] = session.execute(
            delete(Project).where(Project.id.in_(project_ids))
        ).rowcount or 0

    deleted["seed_executions"] = session.execute(
        delete(SeedExecution).where(SeedExecution.id == previous.id)
    ).rowcount or 0
    session.flush()
    return deleted


def upsert_projects(
    session: Session,
    catalog: list[dict[str, Any]],
) -> dict[str, UUID]:
    """Insert/update projects. Returns map normalized_name → project_id."""
    name_to_id: dict[str, UUID] = {}
    stages: list[ProjectStage] = []
    prices: list[ProjectPrice] = []
    assets: list[ProjectAsset] = []

    existing_by_slug = {
        row.canonical_slug: row
        for row in session.scalars(select(Project)).all()
    }
    existing_by_id = {row.id: row for row in existing_by_slug.values()}

    for item in catalog:
        name = strip_text(item.get("nombre")) or "Proyecto sin nombre"
        project_id = parse_optional_uuid(item.get("id")) or uuid4()
        slug = slugify_project(name)
        existing = existing_by_id.get(project_id) or existing_by_slug.get(slug)
        metadata = {
            "source": "projects_catalog",
            "historical_rows": (item.get("metadata") or {}).get("historical_rows"),
            "catalog_etapa": item.get("etapa"),
            "catalog_ubicacion": item.get("ubicacion"),
            "catalog_municipio": item.get("municipio"),
            "catalog_departamento": item.get("departamento"),
        }
        if existing is None:
            existing = Project(
                id=project_id,
                canonical_slug=slug,
                name=name,
                code=strip_text(item.get("codigo")),
                available=bool(item.get("disponible", True)),
                project_type="housing",
                metadata_=metadata,
            )
            session.add(existing)
            existing_by_slug[slug] = existing
            existing_by_id[project_id] = existing
        else:
            existing.name = name
            existing.code = strip_text(item.get("codigo"))
            existing.available = bool(item.get("disponible", True))
            existing.metadata_ = {**(existing.metadata_ or {}), **metadata}
            project_id = existing.id

        etapa = strip_text(item.get("etapa"))
        if etapa:
            stages.append(
                ProjectStage(
                    project_id=project_id,
                    name=etapa,
                    available=True,
                    status="historical",
                )
            )

        min_price = parse_optional_decimal(item.get("valor_minimo"))
        max_price = parse_optional_decimal(item.get("valor_maximo"))
        if min_price is not None or max_price is not None:
            reliable = False
            if min_price is not None and max_price is not None:
                reliable = max_price <= Decimal("1000000000")
            prices.append(
                ProjectPrice(
                    project_id=project_id,
                    minimum_price=min_price,
                    maximum_price=max_price,
                    currency="COP",
                    source="buyers_history",
                    reliable=reliable,
                )
            )

        for asset_type, url_key in (
            ("brochure", "brochure_url"),
            ("tour_360", "recorrido_360_url"),
        ):
            url = strip_text(item.get(url_key))
            if not url:
                continue
            assets.append(
                ProjectAsset(
                    project_id=project_id,
                    asset_type=asset_type,
                    url=url,
                    label=asset_type,
                    is_primary=True,
                    is_active=True,
                )
            )

        key = normalize_project_name(name) or name.lower()
        name_to_id[key] = project_id

    session.flush()
    if stages:
        session.add_all(stages)
    if prices:
        session.add_all(prices)
    if assets:
        session.add_all(assets)
    session.flush()
    print(f"  proyectos upsert: {len(name_to_id)}")
    return name_to_id


def create_import_batch(
    session: Session,
    *,
    buyers_path: Path,
    checksum: str,
    total_records: int,
) -> ImportBatch:
    now = datetime.now(UTC)
    batch = ImportBatch(
        source_name=DATA_SOURCE_CODE,
        file_name=buyers_path.name,
        file_checksum=checksum,
        status="processing",
        total_records=total_records,
        valid_records=0,
        invalid_records=0,
        started_at=now,
        metadata_={
            "seed_name": SEED_NAME,
            "seed_version": SEED_VERSION,
            "source_path": str(buyers_path),
        },
    )
    session.add(batch)
    session.flush()
    return batch


def insert_persons(
    session: Session,
    *,
    person_rows: list[dict[str, Any]],
) -> dict[int, UUID]:
    """Insert synthetic persons + identity/affiliation rows. Returns row→person_id."""
    row_to_person: dict[int, UUID] = {}
    person_buffer: list[dict[str, Any]] = []
    identifier_buffer: list[dict[str, Any]] = []
    contact_buffer: list[dict[str, Any]] = []
    affiliation_buffer: list[dict[str, Any]] = []
    employer_buffer: list[dict[str, Any]] = []

    def flush_buffers() -> None:
        nonlocal person_buffer, identifier_buffer, contact_buffer
        nonlocal affiliation_buffer, employer_buffer
        if person_buffer:
            session.execute(pg_insert(Person), person_buffer)
            person_buffer = []
        if identifier_buffer:
            session.execute(pg_insert(PersonIdentifier), identifier_buffer)
            identifier_buffer = []
        if contact_buffer:
            session.execute(pg_insert(ContactPoint), contact_buffer)
            contact_buffer = []
        if affiliation_buffer:
            session.execute(pg_insert(AffiliationRecord), affiliation_buffer)
            affiliation_buffer = []
        if employer_buffer:
            session.execute(pg_insert(AffiliationEmployer), employer_buffer)
            employer_buffer = []
        session.flush()
        print(f"  personas insertadas: {len(row_to_person)}")

    for row in person_rows:
        row_number = int(row["row_number"])
        person_id = UUID(str(row["person_id"]))
        row_to_person[row_number] = person_id
        person_buffer.append(
            {
                "id": person_id,
                "first_name": strip_text(row.get("first_name")),
                "last_name": strip_text(row.get("last_name")),
                "display_name": strip_text(row.get("display_name")),
                "identity_status": strip_text(row.get("identity_status"))
                or "not_checked",
                "is_demo": bool(row.get("is_demo", True)),
            }
        )
        identifier = row.get("identifier") or {}
        identifier_buffer.append(
            {
                "id": uuid4(),
                "person_id": person_id,
                "identifier_type": strip_text(identifier.get("identifier_type")) or "CC",
                "identifier_hash": strip_text(identifier.get("identifier_hash")) or "",
                "identifier_ciphertext": strip_text(
                    identifier.get("identifier_ciphertext")
                ),
                "identifier_last_four": strip_text(
                    identifier.get("identifier_last_four")
                ),
                "country_code": strip_text(identifier.get("country_code")) or "CO",
                "is_primary": bool(identifier.get("is_primary", True)),
                "is_verified": bool(identifier.get("is_verified", False)),
            }
        )
        for contact in row.get("contacts") or []:
            contact_buffer.append(
                {
                    "id": uuid4(),
                    "person_id": person_id,
                    "contact_type": strip_text(contact.get("contact_type")) or "phone",
                    "value_hash": strip_text(contact.get("value_hash")) or "",
                    "value_ciphertext": strip_text(contact.get("value_ciphertext")),
                    "masked_value": strip_text(contact.get("masked_value")),
                    "is_primary": bool(contact.get("is_primary", True)),
                    "is_verified": bool(contact.get("is_verified", False)),
                }
            )
        affiliation = row.get("affiliation") or {}
        affiliation_id = uuid4()
        category = strip_text(affiliation.get("category"))
        if category not in {"A", "B", "C", "D"}:
            category = None
        affiliation_buffer.append(
            {
                "id": affiliation_id,
                "person_id": person_id,
                "provider": strip_text(affiliation.get("provider"))
                or "mock_affiliation_service",
                "status": strip_text(affiliation.get("status")) or "unknown",
                "category": category,
                "reported_salary": parse_optional_decimal(
                    affiliation.get("reported_salary")
                ),
                "confirmed": bool(affiliation.get("confirmed", False)),
                "source_reference": strip_text(affiliation.get("source_reference")),
            }
        )
        employer_name = strip_text(affiliation.get("employer_name"))
        if employer_name:
            employer_buffer.append(
                {
                    "id": uuid4(),
                    "affiliation_record_id": affiliation_id,
                    "employer_name": employer_name,
                    "reported_salary": parse_optional_decimal(
                        affiliation.get("reported_salary")
                    ),
                    "is_current": True,
                }
            )

        if len(person_buffer) >= CHUNK_SIZE:
            flush_buffers()

    flush_buffers()
    return row_to_person


def insert_buyer_records(
    session: Session,
    *,
    batch: ImportBatch,
    records: list[dict[str, Any]],
    project_ids: dict[str, UUID],
    person_ids_by_row: dict[int, UUID],
) -> tuple[int, int]:
    inserted = 0
    invalid = 0
    buffer: list[dict[str, Any]] = []

    def flush_buffer() -> None:
        nonlocal buffer
        if not buffer:
            return
        session.execute(pg_insert(NormalizedBuyerRecord), buffer)
        session.flush()
        print(f"  buyers insertados: {inserted}")
        buffer = []

    for record in records:
        project_name = strip_text(record.get("original_project_name"))
        project_key = normalize_project_name(project_name) if project_name else None
        historical_project_id = project_ids.get(project_key) if project_key else None
        row_number = int(record.get("row_number", inserted))
        try:
            buffer.append(
                {
                    "id": uuid4(),
                    "batch_id": batch.id,
                    "row_number": row_number,
                    "person_id": person_ids_by_row.get(row_number),
                    "historical_project_id": historical_project_id,
                    "original_project_name": project_name,
                    "affiliation_status": strip_text(record.get("affiliation_status")),
                    "affiliation_category": strip_text(
                        record.get("affiliation_category")
                    ),
                    "commercial_segment": strip_text(record.get("commercial_segment")),
                    "salary_range": strip_text(record.get("salary_range")),
                    "dependents": (
                        int(record["dependents"])
                        if record.get("dependents") is not None
                        else None
                    ),
                    "company_name": strip_text(record.get("company_name")),
                    "financial_entity": strip_text(record.get("financial_entity")),
                    "housing_value": parse_optional_decimal(record.get("housing_value")),
                    "housing_value_reliable": bool(
                        record.get("housing_value_reliable", False)
                    ),
                    "option_date": parse_optional_date(record.get("option_date")),
                    "desistment_date": parse_optional_date(
                        record.get("desistment_date")
                    ),
                    "normalized_data": record.get("normalized_data") or {},
                }
            )
            inserted += 1
        except Exception:  # noqa: BLE001 - count and continue for resilient seed
            invalid += 1
            continue

        if len(buffer) >= CHUNK_SIZE:
            flush_buffer()

    flush_buffer()
    batch.valid_records = inserted
    batch.invalid_records = invalid
    batch.status = "completed"
    batch.completed_at = datetime.now(UTC)
    session.flush()
    return inserted, invalid


def resolve_person_rows(
    *,
    persons_path: Path,
    buyers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Load persons_seed.json or synthesize deterministically from buyers."""
    if persons_path.exists():
        payload = load_json(persons_path)
        if isinstance(payload, dict) and isinstance(payload.get("persons"), list):
            return payload["persons"]
        if isinstance(payload, list):
            return payload
        raise ValueError("persons_seed.json inválido: se esperaba {persons: [...]} ")

    print(
        f"No existe {persons_path}; generando personas sintéticas en memoria "
        f"desde {len(buyers)} buyers…"
    )
    rows: list[dict[str, Any]] = []
    for record in buyers:
        row_number = int(record.get("row_number", len(rows)))
        normalized = record.get("normalized_data") or {}
        age_range = None
        segment = strip_text(record.get("commercial_segment"))
        if isinstance(normalized, dict):
            age_range = strip_text(normalized.get("rango_edad"))
            segment = segment or strip_text(normalized.get("segmento_codigo"))
        draft = build_synthetic_person(
            row_number=row_number,
            person_id=str(person_uuid_for_row(row_number)),
            affiliated=affiliated_from_buyer_record(record),
            dependents=(
                int(record["dependents"])
                if record.get("dependents") is not None
                else None
            ),
            age_range=age_range,
            segment=segment,
            company_hint=strip_text(record.get("company_name")),
        )
        rows.append(draft_to_person_seed(draft))
    return rows


def insert_profiles(
    session: Session,
    *,
    profiles_payload: dict[str, Any],
    project_ids: dict[str, UUID],
    batch_id: UUID,
) -> tuple[int, int]:
    catalog_profiles = profiles_payload.get("catalog_profiles") or []
    profiles_inserted = 0
    distributions_inserted = 0
    generated_at = datetime.now(UTC)
    generated_raw = strip_text(profiles_payload.get("generated_at"))
    if generated_raw:
        try:
            generated_at = datetime.fromisoformat(generated_raw.replace("Z", "+00:00"))
        except ValueError:
            pass

    distribution_rows: list[dict[str, Any]] = []

    for profile in catalog_profiles:
        catalog_name = strip_text(profile.get("catalog_name") or profile.get("project_name"))
        if not catalog_name:
            continue
        key = normalize_project_name(catalog_name) or catalog_name.lower()
        project_id = project_ids.get(key)
        if project_id is None:
            explicit_id = parse_optional_uuid(profile.get("project_id"))
            project_id = explicit_id
        if project_id is None:
            continue

        sample_size = int(profile.get("total_buyers") or 0)
        hist = ProjectHistoricalProfile(
            project_id=project_id,
            sample_size=sample_size,
            affiliated_percentage=parse_optional_decimal(
                profile.get("affiliated_percentage")
            ),
            non_affiliated_percentage=parse_optional_decimal(
                profile.get("non_affiliated_percentage")
            ),
            desistment_percentage=parse_optional_decimal(
                profile.get("withdrawal_percentage")
            ),
            profile_data=profile,
            source_batch_id=batch_id,
            generated_at=generated_at,
        )
        session.add(hist)
        session.flush()
        profiles_inserted += 1

        for field_name, dimension in DISTRIBUTION_FIELDS:
            dist = profile.get(field_name) or {}
            if not isinstance(dist, dict):
                continue
            for value, percentage in dist.items():
                pct = parse_optional_decimal(percentage)
                if pct is None:
                    continue
                record_count = int(round(float(pct) / 100.0 * sample_size))
                distribution_rows.append(
                    {
                        "id": uuid4(),
                        "historical_profile_id": hist.id,
                        "dimension": dimension,
                        "value": str(value)[:255],
                        "record_count": max(record_count, 0),
                        "percentage": pct,
                        "metadata": {},
                    }
                )
                distributions_inserted += 1

    if distribution_rows:
        for start in range(0, len(distribution_rows), CHUNK_SIZE):
            chunk = distribution_rows[start : start + CHUNK_SIZE]
            session.execute(pg_insert(ProjectProfileDistribution), chunk)
            session.flush()
    print(f"  perfiles: {profiles_inserted} | distribuciones: {distributions_inserted}")
    return profiles_inserted, distributions_inserted


def main() -> int:
    _configure_stdout()
    args = parse_args()
    settings = get_settings()

    buyers_path = Path(args.buyers_seed)
    projects_path = Path(args.projects)
    profiles_path = Path(args.profiles)
    persons_path = Path(args.persons_seed)
    for path in (buyers_path, projects_path, profiles_path):
        if not path.exists():
            print(f"No existe: {path}")
            return 1

    buyers = load_json(buyers_path)
    projects = load_json(projects_path)
    profiles = load_json(profiles_path)
    if not isinstance(buyers, list):
        print("buyers_seed.json debe ser una lista de registros.")
        return 1
    if not isinstance(projects, list):
        print("projects_catalog.json debe ser una lista.")
        return 1
    if not isinstance(profiles, dict) or "catalog_profiles" not in profiles:
        print("project_profiles.json debe incluir catalog_profiles.")
        return 1

    try:
        person_rows = resolve_person_rows(persons_path=persons_path, buyers=buyers)
    except ValueError as exc:
        print(str(exc))
        return 1

    checksum_paths = [buyers_path, projects_path, profiles_path]
    if persons_path.exists():
        checksum_paths.append(persons_path)
    checksum = combined_checksum(checksum_paths)
    print(f"Checksum: {checksum[:16]}…")
    print(
        f"Proyectos: {len(projects)} | Compradores: {len(buyers)} | "
        f"Personas: {len(person_rows)} | "
        f"Perfiles: {len(profiles.get('catalog_profiles') or [])}"
    )

    if args.dry_run:
        print("Dry-run: validación OK, no se escribió en PostgreSQL.")
        return 0

    url = settings.get_database_url()
    if not url:
        print("DATABASE_URL no está configurada.")
        return 1

    sync_url = url.replace("postgresql+psycopg://", "postgresql://", 1)
    print(f"Conectando a: {settings.get_redacted_database_url()}")
    engine = create_engine(
        sync_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 30},
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    try:
        with SessionLocal() as session:
            existing = find_seed_by_checksum(session, checksum)
            if existing is not None and existing.status == "completed" and not args.force:
                print(
                    "Seed ya aplicado (mismo checksum). "
                    "Usa --force para reemplazarlo."
                )
                print(f"SeedExecution id={existing.id}")
                return 0

            previous_seeds = find_seeds_by_name_version(session)
            incomplete_same = [
                row
                for row in previous_seeds
                if row.checksum == checksum and row.status != "completed"
            ]
            if incomplete_same and not args.force:
                print(
                    "Hay un seed incompleto con el mismo checksum "
                    f"(status={incomplete_same[0].status}). Usa --force para reintentar."
                )
                return 1
            if previous_seeds and not args.force and existing is None:
                print(
                    f"Ya existe {len(previous_seeds)} seed(s) "
                    f"'{SEED_NAME}' v{SEED_VERSION} con otro checksum. "
                    "Usa --force para reemplazar."
                )
                return 1

            if args.force:
                for previous in find_seeds_by_name(session):
                    purged = purge_previous_seed(session, previous)
                    print(
                        f"Purgado seed previo {previous.id} "
                        f"(v{previous.seed_version}): {purged}"
                    )
            elif incomplete_same:
                for previous in incomplete_same:
                    purged = purge_previous_seed(session, previous)
                    print(f"Purgado seed incompleto {previous.id}: {purged}")

            started_at = datetime.now(UTC)
            seed_row = SeedExecution(
                seed_name=SEED_NAME,
                seed_version=SEED_VERSION,
                checksum=checksum,
                status="running",
                records_inserted=0,
                records_updated=0,
                records_skipped=0,
                started_at=started_at,
                metadata_={
                    "buyers_seed": str(buyers_path),
                    "projects": str(projects_path),
                    "profiles": str(profiles_path),
                    "persons_seed": str(persons_path),
                },
            )
            session.add(seed_row)
            session.flush()

            ensure_data_source(session)
            print("Upsert de proyectos…")
            project_ids = upsert_projects(session, projects)
            print("Insertando personas sintéticas…")
            person_ids_by_row = insert_persons(session, person_rows=person_rows)
            print("Creando import batch…")
            batch = create_import_batch(
                session,
                buyers_path=buyers_path,
                checksum=checksum,
                total_records=len(buyers),
            )
            print("Insertando compradores…")
            buyers_inserted, buyers_invalid = insert_buyer_records(
                session,
                batch=batch,
                records=buyers,
                project_ids=project_ids,
                person_ids_by_row=person_ids_by_row,
            )
            print("Insertando perfiles históricos…")
            profiles_inserted, distributions_inserted = insert_profiles(
                session,
                profiles_payload=profiles,
                project_ids=project_ids,
                batch_id=batch.id,
            )

            seed_row.status = "completed"
            seed_row.completed_at = datetime.now(UTC)
            seed_row.records_inserted = (
                len(project_ids)
                + len(person_ids_by_row)
                + buyers_inserted
                + profiles_inserted
                + distributions_inserted
            )
            seed_row.records_skipped = buyers_invalid
            seed_row.metadata_ = {
                **(seed_row.metadata_ or {}),
                "import_batch_id": str(batch.id),
                "project_ids": [str(value) for value in project_ids.values()],
                "person_ids": [str(value) for value in person_ids_by_row.values()],
                "projects_upserted": len(project_ids),
                "persons_inserted": len(person_ids_by_row),
                "buyers_inserted": buyers_inserted,
                "buyers_invalid": buyers_invalid,
                "profiles_inserted": profiles_inserted,
                "distributions_inserted": distributions_inserted,
            }
            session.commit()

            print("Seed completado.")
            print(f"  projects: {len(project_ids)}")
            print(f"  persons: {len(person_ids_by_row)}")
            print(f"  buyers: {buyers_inserted} (invalidas: {buyers_invalid})")
            print(f"  profiles: {profiles_inserted}")
            print(f"  distributions: {distributions_inserted}")
            print(f"  import_batch_id: {batch.id}")
            print(f"  seed_execution_id: {seed_row.id}")
            return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Seed FALLÓ: {type(exc).__name__}: {exc}")
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
