"""Prepare and normalize Excel datasets into processed artifacts.

Usage:
    python scripts/prepare_data.py --buyers "RUTA_ARCHIVO" --brochures "RUTA_ARCHIVO"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402
from app.utils.normalization import (  # noqa: E402
    normalize_affiliation_flag,
    normalize_for_comparison,
    parse_money_value,
    strip_text,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normaliza Excel del reto y genera artefactos en data/processed.",
    )
    parser.add_argument("--buyers", type=str, required=True, help="Ruta Excel compradores")
    parser.add_argument("--brochures", type=str, help="Ruta Excel brochures/links")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directorio de salida (default: PROCESSED_DATA_PATH)",
    )
    return parser.parse_args()


def normalize_header(value: Any) -> str:
    text = strip_text(value) or "unnamed"
    text = re.sub(r"\s+", " ", text)
    return text


def build_column_mapping(columns: list[str]) -> dict[str, str]:
    """Map original headers to snake-ish normalized keys while keeping originals elsewhere."""
    mapping: dict[str, str] = {}
    used: set[str] = set()
    for column in columns:
        base = normalize_for_comparison(column) or "unnamed"
        key = re.sub(r"[^a-z0-9]+", "_", base).strip("_") or "unnamed"
        candidate = key
        suffix = 2
        while candidate in used:
            candidate = f"{key}_{suffix}"
            suffix += 1
        used.add(candidate)
        mapping[column] = candidate
    return mapping


def infer_semantic_role(normalized_name: str) -> str | None:
    # Order matters: more specific roles first.
    rules: list[tuple[str, tuple[str, ...]]] = [
        ("proyecto", ("nombre_proyecto", "proyecto", "project", "desarrollo")),
        ("afiliacion", ("estado_afiliacion",)),
        ("segmento", ("segmento", "segment")),
        ("categoria", ("categoria",)),
        ("rango_salarial", ("rango_salarial",)),
        ("salario", ("salario_mensual", "salario", "ingreso")),
        ("personas_a_cargo", ("beneficiar", "personas_a_cargo", "depend")),
        ("empresa", ("nombre_empresa", "empresa", "empleador")),
        ("entidad_financiera", ("ent_credito", "entidad", "banco", "financ")),
        ("valor_vivienda", ("vlr_vivienda", "valor_vivienda", "precio_vivienda")),
        ("fecha_opcion", ("fec_opcion", "fecha_opcion", "opcion")),
        ("fecha_desistimiento", ("fecha_desistimiento", "desist")),
        ("medio_conocimiento", ("medio", "conoce", "canal")),
        ("etapa", ("etapa",)),
        ("municipio", ("municipio", "ciudad")),
        ("departamento", ("departamento",)),
        ("brochure", ("brochure", "folleto")),
        ("recorrido_360", ("360", "recorrido", "tour")),
        ("ubicacion", ("ubicacion", "zona", "localidad")),
    ]
    for role, hints in rules:
        if any(hint in normalized_name for hint in hints):
            return role
    return None


def convert_dates(series: pd.Series) -> tuple[pd.Series, list[str]]:
    warnings: list[str] = []
    converted = pd.to_datetime(series, errors="coerce", dayfirst=True)
    failed = series.notna() & converted.isna()
    failed_count = int(failed.sum())
    if failed_count:
        warnings.append(
            f"Columna '{series.name}': {failed_count} fechas no interpretables"
        )
    return converted, warnings


def prepare_buyers(path: Path) -> tuple[pd.DataFrame, dict[str, Any], list[str]]:
    warnings: list[str] = []
    raw = pd.read_excel(path)
    original_columns = [normalize_header(c) for c in raw.columns]
    raw.columns = original_columns
    mapping = build_column_mapping(original_columns)

    working = raw.copy()
    # Keep originals under *_original and normalized helper columns.
    for original, normalized in mapping.items():
        working[f"{normalized}_original"] = working[original].apply(strip_text)
        working[normalized] = working[original]

    semantic_map: dict[str, str] = {}
    for _original, normalized in mapping.items():
        role = infer_semantic_role(normalized)
        if role and role not in semantic_map:
            semantic_map[role] = normalized

    # Normalize affiliation equivalents without silently forcing ambiguous values.
    if "afiliacion" in semantic_map:
        col = semantic_map["afiliacion"]
        parsed = working[col].apply(normalize_affiliation_flag)
        ambiguous = working[col].notna() & parsed.isna()
        ambiguous_count = int(ambiguous.sum())
        if ambiguous_count:
            warnings.append(
                f"Afiliación: {ambiguous_count} valores ambiguos no unificados automáticamente"
            )
        working["afiliado_normalizado"] = parsed

    # Money-like columns (skip categorical salary ranges).
    for role in ("valor_vivienda", "salario"):
        if role not in semantic_map:
            continue
        col = semantic_map[role]
        amounts: list[float | None] = []
        money_warning_count = 0
        sample_warnings: list[str] = []
        for value in working[col].tolist():
            amount, warning = parse_money_value(value)
            amounts.append(amount)
            if warning:
                money_warning_count += 1
                if len(sample_warnings) < 5:
                    sample_warnings.append(warning)
        working[f"{col}_numerico"] = amounts
        if money_warning_count:
            warnings.append(
                f"{col}: {money_warning_count} valores monetarios no interpretables. "
                f"Ejemplos: {sample_warnings}"
            )

    # Date-like columns
    for role in ("fecha_opcion", "fecha_desistimiento"):
        if role not in semantic_map:
            continue
        col = semantic_map[role]
        converted, date_warnings = convert_dates(working[col])
        warnings.extend(date_warnings)
        working[f"{col}_fecha"] = converted

    return working, {"column_mapping": mapping, "semantic_map": semantic_map}, warnings


def prepare_projects(
    buyers_df: pd.DataFrame,
    buyers_meta: dict[str, Any],
    brochures_path: Path | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    semantic_map: dict[str, str] = buyers_meta.get("semantic_map", {})
    project_col = semantic_map.get("proyecto")

    brochure_by_name: dict[str, dict[str, Any]] = {}
    if brochures_path is not None:
        if not brochures_path.exists():
            warnings.append(f"Brochures no encontrado: {brochures_path}")
        else:
            brochure_df = pd.read_excel(brochures_path)
            brochure_df.columns = [normalize_header(c) for c in brochure_df.columns]
            name_col = next(
                (
                    c
                    for c in brochure_df.columns
                    if infer_semantic_role(normalize_for_comparison(c) or "")
                    in {"proyecto", None}
                    and "proyecto" in (normalize_for_comparison(c) or "")
                ),
                brochure_df.columns[0] if len(brochure_df.columns) else None,
            )
            url_col = next(
                (
                    c
                    for c in brochure_df.columns
                    if any(
                        token in (normalize_for_comparison(c) or "")
                        for token in ("url", "link", "brochure", "folleto", "http")
                    )
                ),
                None,
            )
            tour_col = next(
                (
                    c
                    for c in brochure_df.columns
                    if any(
                        token in (normalize_for_comparison(c) or "")
                        for token in ("360", "recorrido", "tour")
                    )
                ),
                None,
            )
            if name_col is None:
                warnings.append("No se pudo identificar columna de proyecto en brochures")
            else:
                for _, row in brochure_df.iterrows():
                    name = strip_text(row.get(name_col))
                    if not name:
                        continue
                    key = normalize_for_comparison(name) or name
                    brochure_by_name[key] = {
                        "nombre": name,
                        "brochure_url": strip_text(row.get(url_col)) if url_col else None,
                        "recorrido_360_url": (
                            strip_text(row.get(tour_col)) if tour_col else None
                        ),
                        "metadata": {
                            str(col): strip_text(row.get(col)) for col in brochure_df.columns
                        },
                    }

    projects: dict[str, dict[str, Any]] = {}

    if project_col and project_col in buyers_df.columns:
        grouped = buyers_df.groupby(project_col, dropna=False)
        for project_name, group in grouped:
            name = strip_text(project_name) or "Proyecto sin nombre"
            key = normalize_for_comparison(name) or name
            affiliated = None
            if "afiliado_normalizado" in group.columns:
                known = group["afiliado_normalizado"].dropna()
                if not known.empty:
                    affiliated = round(float(known.mean() * 100), 2)

            salary_dist: dict[str, float] = {}
            salary_col = semantic_map.get("salario")
            if salary_col and salary_col in group.columns:
                counts = group[salary_col].dropna().astype(str).value_counts(normalize=True)
                salary_dist = {str(k): round(float(v * 100), 2) for k, v in counts.items()}

            segment_dist: dict[str, float] = {}
            segment_col = semantic_map.get("segmento")
            if segment_col and segment_col in group.columns:
                counts = group[segment_col].dropna().astype(str).value_counts(normalize=True)
                segment_dist = {str(k): round(float(v * 100), 2) for k, v in counts.items()}

            dependents_dist: dict[str, float] = {}
            dep_col = semantic_map.get("personas_a_cargo")
            if dep_col and dep_col in group.columns:
                counts = group[dep_col].dropna().astype(str).value_counts(normalize=True)
                dependents_dist = {
                    str(k): round(float(v * 100), 2) for k, v in counts.items()
                }

            def top_values(
                frame: pd.DataFrame,
                role: str,
                n: int = 5,
            ) -> list[str]:
                col = semantic_map.get(role)
                if not col or col not in frame.columns:
                    return []
                return [
                    str(v)
                    for v in frame[col].dropna().astype(str).value_counts().head(n).index
                ]

            valor_min = None
            valor_max = None
            money_col = semantic_map.get("valor_vivienda")
            if money_col and f"{money_col}_numerico" in group.columns:
                numeric = group[f"{money_col}_numerico"].dropna()
                if not numeric.empty:
                    valor_min = float(numeric.min())
                    valor_max = float(numeric.max())

            brochure = brochure_by_name.get(key, {})
            etapa_values = top_values(group, "etapa", 1)
            ubicacion_values = top_values(group, "ubicacion", 1)
            municipio_values = top_values(group, "municipio", 1)
            departamento_values = top_values(group, "departamento", 1)
            projects[key] = {
                "id": str(uuid.uuid4()),
                "nombre": name,
                "codigo": None,
                "etapa": etapa_values[0] if etapa_values else None,
                "ubicacion": ubicacion_values[0] if ubicacion_values else None,
                "municipio": municipio_values[0] if municipio_values else None,
                "departamento": departamento_values[0] if departamento_values else None,
                "valor_minimo": valor_min,
                "valor_maximo": valor_max,
                "brochure_url": brochure.get("brochure_url"),
                "recorrido_360_url": brochure.get("recorrido_360_url"),
                "disponible": True,
                "perfil_historico": {
                    "affiliated_percentage": affiliated,
                    "salary_range_distribution": salary_dist,
                    "segments": segment_dist,
                    "dependents_distribution": dependents_dist,
                    "frequent_locations": top_values(group, "ubicacion"),
                    "frequent_financial_entities": top_values(group, "entidad_financiera"),
                    "frequent_companies": top_values(group, "empresa"),
                },
                "metadata": {
                    "historical_rows": int(len(group)),
                    "source": "buyers_history",
                },
            }
    else:
        warnings.append(
            "No se detectó columna de proyecto en compradores; "
            "el catálogo se armará solo con brochures si existen."
        )

    # Include brochure-only projects.
    for key, brochure in brochure_by_name.items():
        if key in projects:
            continue
        projects[key] = {
            "id": str(uuid.uuid4()),
            "nombre": brochure["nombre"],
            "codigo": None,
            "etapa": None,
            "ubicacion": None,
            "municipio": None,
            "departamento": None,
            "valor_minimo": None,
            "valor_maximo": None,
            "brochure_url": brochure.get("brochure_url"),
            "recorrido_360_url": brochure.get("recorrido_360_url"),
            "disponible": True,
            "perfil_historico": {
                "affiliated_percentage": None,
                "salary_range_distribution": {},
                "segments": {},
                "dependents_distribution": {},
                "frequent_locations": [],
                "frequent_financial_entities": [],
                "frequent_companies": [],
            },
            "metadata": brochure.get("metadata", {}),
        }

    return list(projects.values()), warnings


def dataframe_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in df.to_dict(orient="records"):
        clean: dict[str, Any] = {}
        for key, value in row.items():
            if pd.isna(value):
                clean[str(key)] = None
            elif isinstance(value, pd.Timestamp):
                clean[str(key)] = value.isoformat()
            else:
                clean[str(key)] = value
        records.append(clean)
    return records


def _configure_stdout() -> None:
    """Avoid Windows cp1252 crashes when printing accented data."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    _configure_stdout()
    args = parse_args()
    settings = get_settings()
    output_dir = Path(args.output_dir or settings.processed_data_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    buyers_path = Path(args.buyers)
    if not buyers_path.exists():
        print(f"No existe el archivo de compradores: {buyers_path}")
        return 1

    buyers_df, buyers_meta, buyer_warnings = prepare_buyers(buyers_path)
    brochures_path = Path(args.brochures) if args.brochures else None
    projects, project_warnings = prepare_projects(buyers_df, buyers_meta, brochures_path)
    all_warnings = buyer_warnings + project_warnings

    buyers_csv = output_dir / "buyers_clean.csv"
    buyers_json = output_dir / "buyers_clean.json"
    projects_json = output_dir / "projects_catalog.json"
    quality_json = output_dir / "data_quality_report.json"
    mapping_json = output_dir / "column_mapping.json"

    buyers_df.to_csv(buyers_csv, index=False, encoding="utf-8")
    buyers_json.write_text(
        json.dumps(dataframe_to_records(buyers_df), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    projects_json.write_text(
        json.dumps(projects, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    mapping_json.write_text(
        json.dumps(buyers_meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    quality_report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "inputs": {
            "buyers": str(buyers_path),
            "brochures": str(brochures_path) if brochures_path else None,
        },
        "outputs": {
            "buyers_clean_csv": str(buyers_csv),
            "buyers_clean_json": str(buyers_json),
            "projects_catalog_json": str(projects_json),
            "column_mapping_json": str(mapping_json),
        },
        "buyers_rows": int(len(buyers_df)),
        "projects_count": len(projects),
        "warnings": all_warnings,
        "notes": [
            "Los archivos originales no fueron modificados.",
            "Valores ambiguos no se corrigen en silencio; se registran como advertencias.",
            (
                "Esta base contiene principalmente compradores históricos y "
                "desistimientos; no representa todos los leads que nunca compraron."
            ),
            "No se entrenó ningún modelo predictivo en esta fase.",
        ],
    }
    quality_json.write_text(
        json.dumps(quality_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Generado: {buyers_csv}")
    print(f"Generado: {buyers_json}")
    print(f"Generado: {projects_json}")
    print(f"Generado: {mapping_json}")
    print(f"Generado: {quality_json}")
    print(f"Advertencias: {len(all_warnings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
