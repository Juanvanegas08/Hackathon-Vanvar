"""Generate synthetic persons for anonymized historical buyer rows.

The hackathon CSV has purchase/profile facts without PII. This script creates
one fictional person per buyers_seed row (deterministic CC / contact data),
writes persons_seed.json for PostgreSQL ingestion, and a historical affiliates
JSON so the mock lookup service can resolve those documents.

Usage:
    python scripts/generate_synthetic_persons.py
    python scripts/generate_synthetic_persons.py --buyers-seed data/processed/buyers_seed.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.utils.normalization import strip_text  # noqa: E402
from app.utils.synthetic_persons import (  # noqa: E402
    affiliated_from_buyer_record,
    build_synthetic_person,
    draft_to_affiliate_record,
    draft_to_person_seed,
    person_uuid_for_row,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Genera personas sintéticas 1:1 con buyers_seed y el JSON "
            "de afiliados históricos para el mock lookup."
        ),
    )
    parser.add_argument(
        "--buyers-seed",
        type=str,
        default="data/processed/buyers_seed.json",
        help="Artefacto buyers_seed (default: data/processed/buyers_seed.json)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/processed/persons_seed.json",
        help="Salida persons_seed.json",
    )
    parser.add_argument(
        "--affiliates-output",
        type=str,
        default="data/mock/mock_affiliates_historical.json",
        help="Salida JSON para mock affiliation lookup",
    )
    return parser.parse_args()


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def build_from_buyers(buyers: list[dict]) -> tuple[list[dict], list[dict]]:
    persons: list[dict] = []
    affiliates: list[dict] = []
    for record in buyers:
        row_number = int(record.get("row_number", len(persons)))
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
        persons.append(draft_to_person_seed(draft))
        affiliates.append(draft_to_affiliate_record(draft))
    return persons, affiliates


def main() -> int:
    _configure_stdout()
    args = parse_args()
    buyers_path = Path(args.buyers_seed)
    if not buyers_path.exists():
        print(f"No existe buyers_seed: {buyers_path}")
        print("Ejecuta primero: python scripts/prepare_data.py --buyers ...")
        return 1

    buyers = json.loads(buyers_path.read_text(encoding="utf-8"))
    if not isinstance(buyers, list):
        print("buyers_seed.json debe ser una lista.")
        return 1

    persons, affiliates = build_from_buyers(buyers)
    output_path = Path(args.output)
    affiliates_path = Path(args.affiliates_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    affiliates_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "generated_from": str(buyers_path).replace("\\", "/"),
        "total_persons": len(persons),
        "note": (
            "Personas 100% ficticias enlazadas 1:1 con filas del CSV histórico "
            "vía row_number / person_id."
        ),
        "persons": persons,
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    affiliates_path.write_text(
        json.dumps(affiliates, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Generado: {output_path} ({len(persons)} personas)")
    print(f"Generado: {affiliates_path} ({len(affiliates)} afiliados mock)")
    if persons:
        sample = persons[0]
        print(
            f"Ejemplo fila {sample['row_number']}: "
            f"{sample['display_name']} CC {sample['document_number']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
