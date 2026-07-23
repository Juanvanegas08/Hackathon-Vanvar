"""Prepare and normalize Excel/CSV datasets into processed artifacts.

Usage:
    python scripts/prepare_data.py --buyers "RUTA_ARCHIVO" --brochures "RUTA_ARCHIVO"

Supports the hackathon export:
  docs/hackathon_VIVIENDAv2.xlsx - CV_SSS_VIV_PENETRACION_PERFIL_C.csv
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402
from app.utils.normalization import (  # noqa: E402
    infer_affiliation_from_periodo,
    normalize_affiliation_flag,
    normalize_age_range_label,
    normalize_for_comparison,
    normalize_yes_no_flag,
    parse_money_value,
    scale_housing_value,
    strip_text,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normaliza Excel/CSV del reto y genera artefactos en data/processed.",
    )
    parser.add_argument(
        "--buyers",
        type=str,
        required=True,
        help="Ruta Excel/CSV de compradores",
    )
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


def load_tabular(path: Path) -> pd.DataFrame:
    """Load CSV or Excel buyers/brochures without mutating the source file."""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xls", ".xlsm"}:
        return pd.read_excel(path)
    # Fallback: try CSV then Excel for odd export names.
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.read_excel(path)


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
        ("periodo_afiliado", ("periodo_afiliado",)),
        ("afiliacion", ("estado_afiliacion", "estado_afiliado")),
        ("empresa_foco", ("empresa_foco", "foco")),
        ("piramide", ("piramide",)),
        ("rango_edad", ("rango_edad",)),
        ("grupo_familiar", ("grupo_familar", "grupo_familiar")),
        ("segmento", ("segmento_poblacional", "segmento", "segment")),
        ("categoria", ("categoria",)),
        ("rango_salarial", ("rango_salarial",)),
        ("salario", ("salario_mensual", "salario", "ingreso")),
        (
            "personas_a_cargo",
            ("beneficiar", "personas_a_cargo", "depend", "cuota_monetaria"),
        ),
        ("empresa", ("nombre_empresa", "empleador", "razon_social")),
        (
            "entidad_financiera",
            ("ent_credito", "entidad_financiera", "entidad", "banco", "financ"),
        ),
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
        ("periodo", ("periodo",)),
    ]
    for role, hints in rules:
        if any(hint in normalized_name for hint in hints):
            return role
    return None


def convert_dates(series: pd.Series) -> tuple[pd.Series, list[str]]:
    """Parse dates from hackathon exports (mostly US M/D/YYYY) with a dayfirst fallback."""
    warnings: list[str] = []
    # Prefer month-first: values like 2/13/2024 are invalid under dayfirst=True.
    converted = pd.to_datetime(series, errors="coerce", dayfirst=False)
    still_missing = series.notna() & converted.isna()
    if still_missing.any():
        fallback = pd.to_datetime(series[still_missing], errors="coerce", dayfirst=True)
        converted = converted.copy()
        converted.loc[still_missing] = fallback
    failed = series.notna() & converted.isna()
    # Si/No flags are expected for FECHA_DESISTIMIENTO in the hackathon CSV.
    flag_mask = series.map(lambda value: normalize_yes_no_flag(value) is not None)
    real_failures = failed & ~flag_mask
    failed_count = int(real_failures.sum())
    if failed_count:
        warnings.append(
            f"Columna '{series.name}': {failed_count} fechas no interpretables"
        )
    return converted, warnings


def _series_to_python_date(value: Any) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def prepare_buyers(path: Path) -> tuple[pd.DataFrame, dict[str, Any], list[str]]:
    warnings: list[str] = []
    raw = load_tabular(path)
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

    # Affiliation: prefer explicit estado; else infer from PERIODO_AFILIADO.
    afiliado_values: list[bool | None] = [None] * len(working)
    affiliation_source = "none"
    if "afiliacion" in semantic_map:
        col = semantic_map["afiliacion"]
        parsed = working[col].apply(normalize_affiliation_flag)
        ambiguous = working[col].notna() & parsed.isna()
        ambiguous_count = int(ambiguous.sum())
        if ambiguous_count:
            warnings.append(
                f"Afiliación: {ambiguous_count} valores ambiguos no unificados automáticamente"
            )
        afiliado_values = parsed.tolist()
        affiliation_source = "estado_afiliacion"
    elif "periodo_afiliado" in semantic_map:
        col = semantic_map["periodo_afiliado"]
        afiliado_values = [
            infer_affiliation_from_periodo(value) for value in working[col].tolist()
        ]
        affiliation_source = "periodo_afiliado"
        affiliated_count = sum(1 for value in afiliado_values if value is True)
        warnings.append(
            "Afiliación inferida desde PERIODO_AFILIADO "
            f"({affiliated_count} afiliados / {len(afiliado_values) - affiliated_count} no afiliados). "
            "Códigos SEGMENTO/CATEGORIA permanecen ofuscados."
        )
    else:
        warnings.append(
            "No se encontró ESTADO_AFILIACION ni PERIODO_AFILIADO; "
            "afiliado_normalizado queda vacío."
        )
    working["afiliado_normalizado"] = afiliado_values
    working["affiliation_status"] = [
        (
            "affiliated"
            if value is True
            else "non_affiliated"
            if value is False
            else None
        )
        for value in afiliado_values
    ]

    # Desistimiento: hackathon CSV uses Si/No instead of dates.
    desist_flag_values: list[bool | None] = [None] * len(working)
    if "fecha_desistimiento" in semantic_map:
        col = semantic_map["fecha_desistimiento"]
        flags = working[col].apply(normalize_yes_no_flag)
        flag_count = int(flags.notna().sum())
        if flag_count:
            desist_flag_values = flags.tolist()
            working["desistio_normalizado"] = desist_flag_values
            warnings.append(
                f"FECHA_DESISTIMIENTO interpretada como Si/No ({flag_count} filas); "
                "no hay fecha real de desistimiento en el export."
            )
        converted, date_warnings = convert_dates(working[col])
        warnings.extend(date_warnings)
        # Only keep real parsed dates; Si/No become NaT.
        working[f"{col}_fecha"] = converted
    else:
        working["desistio_normalizado"] = desist_flag_values

    # Option date
    if "fecha_opcion" in semantic_map:
        col = semantic_map["fecha_opcion"]
        converted, date_warnings = convert_dates(working[col])
        warnings.extend(date_warnings)
        working[f"{col}_fecha"] = converted

    # Age range unification
    if "rango_edad" in semantic_map:
        col = semantic_map["rango_edad"]
        working["rango_edad_normalizado"] = working[col].apply(normalize_age_range_label)

    # Money-like columns (skip categorical salary ranges).
    for role in ("valor_vivienda", "salario"):
        if role not in semantic_map:
            continue
        col = semantic_map[role]
        amounts: list[float | None] = []
        scaled_amounts: list[float | None] = []
        reliable_flags: list[bool] = []
        money_warning_count = 0
        scale_count = 0
        sample_warnings: list[str] = []
        for value in working[col].tolist():
            amount, warning = parse_money_value(value)
            if warning:
                money_warning_count += 1
                if len(sample_warnings) < 5:
                    sample_warnings.append(warning)
            if role == "valor_vivienda":
                scaled, reliable, scale_note = scale_housing_value(amount)
                if scale_note and scale_note.startswith("Escalado"):
                    scale_count += 1
                amounts.append(amount)
                scaled_amounts.append(scaled)
                reliable_flags.append(reliable)
            else:
                amounts.append(amount)
        working[f"{col}_numerico_raw"] = amounts
        if role == "valor_vivienda":
            working[f"{col}_numerico"] = scaled_amounts
            working["housing_value_reliable"] = reliable_flags
            if scale_count:
                warnings.append(
                    f"{col}: {scale_count} valores escalados /10000 por formato de exportación."
                )
            unreliable = sum(1 for flag in reliable_flags if not flag)
            if unreliable:
                warnings.append(
                    f"{col}: {unreliable} valores fuera de rango plausible tras escalar."
                )
        else:
            working[f"{col}_numerico"] = amounts
        if money_warning_count:
            warnings.append(
                f"{col}: {money_warning_count} valores monetarios no interpretables. "
                f"Ejemplos: {sample_warnings}"
            )

    # Compatibility aliases expected by project_profile_builder.
    if "entidad_financiera" in semantic_map:
        working["ent_credito"] = working[semantic_map["entidad_financiera"]]
    if "empresa" in semantic_map:
        working["nombre_empresa_principal"] = working[semantic_map["empresa"]]
    if "personas_a_cargo" in semantic_map:
        dep_col = semantic_map["personas_a_cargo"]
        working["dependents"] = pd.to_numeric(working[dep_col], errors="coerce")

    if "categoria" in semantic_map or "segmento" in semantic_map:
        warnings.append(
            "CATEGORIA y SEGMENTO_POBLACIONAL vienen ofuscados (códigos tipo OMEGA/KAPPA); "
            "se conservan tal cual hasta tener diccionario oficial."
        )

    meta = {
        "column_mapping": mapping,
        "semantic_map": semantic_map,
        "affiliation_source": affiliation_source,
        "source_format": path.suffix.lower() or "unknown",
    }
    return working, meta, warnings


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
            brochure_df = load_tabular(brochures_path)
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
            salary_col = semantic_map.get("salario") or semantic_map.get("rango_salarial")
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


def build_seed_records(
    buyers_df: pd.DataFrame,
    buyers_meta: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build ingestion-ready records aligned with normalized_buyer_records."""
    semantic_map: dict[str, str] = buyers_meta.get("semantic_map", {})
    project_col = semantic_map.get("proyecto")
    segment_col = semantic_map.get("segmento")
    category_col = semantic_map.get("categoria")
    salary_col = semantic_map.get("rango_salarial")
    financial_col = semantic_map.get("entidad_financiera")
    money_col = semantic_map.get("valor_vivienda")
    option_col = semantic_map.get("fecha_opcion")
    medio_col = semantic_map.get("medio_conocimiento")
    etapa_col = semantic_map.get("etapa")
    piramide_col = semantic_map.get("piramide")
    foco_col = semantic_map.get("empresa_foco")
    edad_col = semantic_map.get("rango_edad")
    grupo_col = semantic_map.get("grupo_familiar")
    periodo_col = semantic_map.get("periodo")
    periodo_af_col = semantic_map.get("periodo_afiliado")

    records: list[dict[str, Any]] = []
    for index, row in buyers_df.iterrows():
        row_number = int(index) if isinstance(index, (int, float)) else len(records)
        option_date = None
        if option_col:
            option_date = _series_to_python_date(row.get(f"{option_col}_fecha"))

        dependents = None
        if "dependents" in buyers_df.columns:
            raw_dep = row.get("dependents")
            if raw_dep is not None and not (isinstance(raw_dep, float) and pd.isna(raw_dep)):
                dependents = int(raw_dep)

        housing_value = None
        if money_col and f"{money_col}_numerico" in buyers_df.columns:
            raw_value = row.get(f"{money_col}_numerico")
            if raw_value is not None and not (
                isinstance(raw_value, float) and pd.isna(raw_value)
            ):
                housing_value = float(raw_value)

        housing_reliable = bool(row.get("housing_value_reliable", False))
        desistio = row.get("desistio_normalizado")
        if isinstance(desistio, float) and pd.isna(desistio):
            desistio = None

        afiliado = row.get("afiliado_normalizado")
        if isinstance(afiliado, float) and pd.isna(afiliado):
            afiliado = None

        normalized_data = {
            "categoria_codigo": strip_text(row.get(category_col)) if category_col else None,
            "segmento_codigo": strip_text(row.get(segment_col)) if segment_col else None,
            "medio": strip_text(row.get(medio_col)) if medio_col else None,
            "etapa": strip_text(row.get(etapa_col)) if etapa_col else None,
            "piramide": strip_text(row.get(piramide_col)) if piramide_col else None,
            "empresa_foco": strip_text(row.get(foco_col)) if foco_col else None,
            "rango_edad": (
                strip_text(row.get("rango_edad_normalizado"))
                if "rango_edad_normalizado" in buyers_df.columns
                else (strip_text(row.get(edad_col)) if edad_col else None)
            ),
            "grupo_familiar": strip_text(row.get(grupo_col)) if grupo_col else None,
            "periodo": strip_text(row.get(periodo_col)) if periodo_col else None,
            "periodo_afiliado": (
                strip_text(row.get(periodo_af_col)) if periodo_af_col else None
            ),
            "desistio": desistio,
            "afiliado": afiliado,
        }

        records.append(
            {
                "row_number": row_number,
                "original_project_name": (
                    strip_text(row.get(project_col)) if project_col else None
                ),
                "affiliation_status": strip_text(row.get("affiliation_status")),
                # Códigos ofuscados no caben en A/B/C/D del schema; van en normalized_data.
                "affiliation_category": None,
                "commercial_segment": (
                    strip_text(row.get(segment_col)) if segment_col else None
                ),
                "salary_range": strip_text(row.get(salary_col)) if salary_col else None,
                "dependents": dependents,
                "company_name": None,
                "financial_entity": (
                    strip_text(row.get(financial_col)) if financial_col else None
                ),
                "housing_value": housing_value,
                "housing_value_reliable": housing_reliable,
                "option_date": option_date.isoformat() if option_date else None,
                "desistment_date": None,
                "normalized_data": normalized_data,
            }
        )
    return records


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
    seed_records = build_seed_records(buyers_df, buyers_meta)
    all_warnings = buyer_warnings + project_warnings

    buyers_csv = output_dir / "buyers_clean.csv"
    buyers_json = output_dir / "buyers_clean.json"
    buyers_seed_json = output_dir / "buyers_seed.json"
    projects_json = output_dir / "projects_catalog.json"
    quality_json = output_dir / "data_quality_report.json"
    mapping_json = output_dir / "column_mapping.json"

    buyers_df.to_csv(buyers_csv, index=False, encoding="utf-8")
    buyers_json.write_text(
        json.dumps(dataframe_to_records(buyers_df), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    buyers_seed_json.write_text(
        json.dumps(seed_records, ensure_ascii=False, indent=2),
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

    affiliated = int(buyers_df["afiliado_normalizado"].fillna(False).astype(bool).sum())
    desisted = 0
    if "desistio_normalizado" in buyers_df.columns:
        desisted = int(buyers_df["desistio_normalizado"].fillna(False).astype(bool).sum())
    reliable_prices = 0
    if "housing_value_reliable" in buyers_df.columns:
        reliable_prices = int(buyers_df["housing_value_reliable"].fillna(False).sum())

    quality_report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "inputs": {
            "buyers": str(buyers_path),
            "brochures": str(brochures_path) if brochures_path else None,
        },
        "outputs": {
            "buyers_clean_csv": str(buyers_csv),
            "buyers_clean_json": str(buyers_json),
            "buyers_seed_json": str(buyers_seed_json),
            "projects_catalog_json": str(projects_json),
            "column_mapping_json": str(mapping_json),
        },
        "buyers_rows": int(len(buyers_df)),
        "projects_count": len(projects),
        "affiliated_count": affiliated,
        "non_affiliated_count": int(len(buyers_df) - affiliated),
        "desisted_count": desisted,
        "housing_value_reliable_count": reliable_prices,
        "affiliation_source": buyers_meta.get("affiliation_source"),
        "warnings": all_warnings,
        "notes": [
            "Los archivos originales no fueron modificados.",
            "Valores ambiguos no se corrigen en silencio; se registran como advertencias.",
            (
                "Esta base contiene principalmente compradores históricos y "
                "desistimientos; no representa todos los leads que nunca compraron."
            ),
            "buyers_seed.json está alineado con ingestion.normalized_buyer_records.",
            "CATEGORIA/SEGMENTO ofuscados se guardan en normalized_data, no en A/B/C/D.",
            "No se entrenó ningún modelo predictivo en esta fase.",
        ],
    }
    quality_json.write_text(
        json.dumps(quality_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Generado: {buyers_csv}")
    print(f"Generado: {buyers_json}")
    print(f"Generado: {buyers_seed_json}")
    print(f"Generado: {projects_json}")
    print(f"Generado: {mapping_json}")
    print(f"Generado: {quality_json}")
    print(f"Filas: {len(buyers_df)} | Proyectos: {len(projects)}")
    print(f"Afiliados: {affiliated} | No afiliados: {len(buyers_df) - affiliated}")
    print(f"Desistimientos: {desisted}")
    print(f"Advertencias: {len(all_warnings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
