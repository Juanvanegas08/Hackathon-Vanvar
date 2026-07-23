"""Pure helpers to build historical project profiles and name matches."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.core.constants import HISTORICAL_PRICE_RELIABILITY_MAX_MEDIAN
from app.utils.project_matching import compare_project_names, normalize_project_name


def distribution(series: pd.Series) -> dict[str, float]:
    """Percentage distribution for categorical values."""
    clean = series.dropna().astype(str).str.strip()
    clean = clean[clean != ""]
    if clean.empty:
        return {}
    counts = clean.value_counts(normalize=True)
    return {str(key): round(float(value * 100), 2) for key, value in counts.items()}


def missing_pct(series: pd.Series) -> float:
    """Percentage of missing values."""
    if len(series) == 0:
        return 100.0
    return round(float(series.isna().mean() * 100), 2)


def build_profile_for_group(group: pd.DataFrame, project_name: str) -> dict[str, Any]:
    """Build one historical profile dictionary from a buyers subset."""
    total = int(len(group))
    affiliated = None
    non_affiliated = None
    if "afiliado_normalizado" in group.columns:
        known = group["afiliado_normalizado"].dropna()
        if not known.empty:
            affiliated = round(float(known.mean() * 100), 2)
            non_affiliated = round(float((1 - known.mean()) * 100), 2)

    dependents_avg = None
    if "no_beneficiarios_cuota_monetaria" in group.columns:
        numeric = pd.to_numeric(group["no_beneficiarios_cuota_monetaria"], errors="coerce")
        if numeric.notna().any():
            dependents_avg = round(float(numeric.mean()), 2)

    price_min = price_max = price_median = None
    price_reliable = False
    if "vlr_vivienda_numerico" in group.columns:
        prices = pd.to_numeric(group["vlr_vivienda_numerico"], errors="coerce").dropna()
        if not prices.empty:
            price_min = float(prices.min())
            price_max = float(prices.max())
            price_median = float(prices.median())
            price_reliable = price_median <= HISTORICAL_PRICE_RELIABILITY_MAX_MEDIAN

    withdrawal = None
    if "fecha_desistimiento_fecha" in group.columns:
        withdrawal = round(float(group["fecha_desistimiento_fecha"].notna().mean() * 100), 2)
    elif "fecha_desistimiento" in group.columns:
        withdrawal = round(float(group["fecha_desistimiento"].notna().mean() * 100), 2)

    missing = {
        "estado_afiliacion": missing_pct(group.get("estado_afiliacion", pd.Series(dtype=object))),
        "categoria": missing_pct(group.get("categoria", pd.Series(dtype=object))),
        "segmento_poblacional": missing_pct(
            group.get("segmento_poblacional", pd.Series(dtype=object))
        ),
        "rango_salarial": missing_pct(group.get("rango_salarial", pd.Series(dtype=object))),
        "no_beneficiarios_cuota_monetaria": missing_pct(
            group.get("no_beneficiarios_cuota_monetaria", pd.Series(dtype=object))
        ),
        "no_grupo_familar": missing_pct(group.get("no_grupo_familar", pd.Series(dtype=object))),
        "vlr_vivienda_numerico": missing_pct(
            group.get("vlr_vivienda_numerico", pd.Series(dtype=object))
        ),
    }

    return {
        "project_name": project_name,
        "normalized_name": normalize_project_name(project_name),
        "total_buyers": total,
        "affiliated_percentage": affiliated,
        "non_affiliated_percentage": non_affiliated,
        "category_distribution": distribution(group.get("categoria", pd.Series(dtype=object))),
        "salary_range_distribution": distribution(
            group.get("rango_salarial", pd.Series(dtype=object))
        ),
        "segments": distribution(group.get("segmento_poblacional", pd.Series(dtype=object))),
        "dependents_distribution": distribution(
            group.get("no_beneficiarios_cuota_monetaria", pd.Series(dtype=object))
        ),
        "dependents_average": dependents_avg,
        "household_composition_distribution": distribution(
            group.get("no_grupo_familar", pd.Series(dtype=object))
        ),
        "frequent_locations": [],
        "frequent_financial_entities": [
            str(v)
            for v in group.get("ent_credito", pd.Series(dtype=object))
            .dropna()
            .astype(str)
            .value_counts()
            .head(5)
            .index
        ],
        "frequent_companies": [
            str(v)
            for v in group.get("nombre_empresa_principal", pd.Series(dtype=object))
            .dropna()
            .astype(str)
            .value_counts()
            .head(5)
            .index
        ],
        "enterprise_pyramid_distribution": distribution(
            group.get("piramide_nueva", pd.Series(dtype=object))
        ),
        "historical_price_min": price_min,
        "historical_price_max": price_max,
        "historical_price_median": price_median,
        "historical_price_reliable": price_reliable,
        "withdrawal_percentage": withdrawal,
        "missing_data_percentage": missing,
        "age_range_distribution": distribution(group.get("rango_edad", pd.Series(dtype=object))),
        "notes": [
            "El porcentaje de desistimiento es histórico y no predice comportamiento futuro.",
            "La categoría A/B/C no debe confundirse con el segmento Básico/Medio/Alto/Joven.",
            "Género/edad/estrato no se usan para puntaje de compatibilidad.",
        ],
    }


def match_catalog_to_history(
    catalog_names: list[str],
    history_names: list[str],
) -> dict[str, Any]:
    """Match catalog project names to historical buyer project names.

    Exact matches are assigned first so short brochure aliases do not steal
    history rows from their full catalog counterparts.
    """
    matched: list[dict[str, Any]] = []
    approximate: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    catalog_without_history: list[str] = []
    assigned_history: set[str] = set()
    assigned_catalog: set[str] = set()

    def _collect_candidates(catalog_name: str) -> list[tuple[str, float, str]]:
        candidates: list[tuple[str, float, str]] = []
        for history_name in history_names:
            if history_name in assigned_history:
                continue
            decision = compare_project_names(catalog_name, history_name)
            if decision.kind in {"exact", "approximate", "ambiguous"}:
                candidates.append((history_name, decision.score, decision.kind))
        candidates.sort(key=lambda item: item[1], reverse=True)
        return candidates

    def _assign(catalog_name: str, history_name: str, score: float, kind: str) -> None:
        record = {
            "catalog_name": catalog_name,
            "history_name": history_name,
            "score": score,
            "kind": kind,
        }
        if kind == "exact":
            matched.append(record)
        else:
            approximate.append(record)
        assigned_history.add(history_name)
        assigned_catalog.add(catalog_name)

    # Pass 1: exact matches only.
    for catalog_name in catalog_names:
        candidates = [
            item for item in _collect_candidates(catalog_name) if item[2] == "exact"
        ]
        if not candidates:
            continue
        top_score = candidates[0][1]
        top_ties = [item for item in candidates if abs(item[1] - top_score) < 0.05]
        if len(top_ties) > 1:
            ambiguous.append(
                {
                    "catalog_name": catalog_name,
                    "candidates": [
                        {"history_name": name, "score": score, "kind": kind}
                        for name, score, kind in top_ties
                    ],
                }
            )
            assigned_catalog.add(catalog_name)
            continue
        history_name, score, kind = candidates[0]
        _assign(catalog_name, history_name, score, kind)

    # Pass 2: approximate / remaining.
    for catalog_name in catalog_names:
        if catalog_name in assigned_catalog:
            continue
        candidates = _collect_candidates(catalog_name)
        if not candidates:
            catalog_without_history.append(catalog_name)
            continue

        top_score = candidates[0][1]
        top_kind = candidates[0][2]
        top_ties = [item for item in candidates if abs(item[1] - top_score) < 0.05]

        if top_kind == "ambiguous" or len(top_ties) > 1:
            ambiguous.append(
                {
                    "catalog_name": catalog_name,
                    "candidates": [
                        {"history_name": name, "score": score, "kind": kind}
                        for name, score, kind in top_ties
                    ],
                }
            )
            continue

        history_name, score, kind = candidates[0]
        if kind in {"exact", "approximate"}:
            _assign(catalog_name, history_name, score, kind)
        else:
            ambiguous.append(
                {
                    "catalog_name": catalog_name,
                    "candidates": [
                        {
                            "history_name": history_name,
                            "score": score,
                            "kind": kind,
                        }
                    ],
                }
            )

    history_without_catalog = [name for name in history_names if name not in assigned_history]
    return {
        "matched": matched,
        "approximate": approximate,
        "ambiguous": ambiguous,
        "catalog_without_history": catalog_without_history,
        "history_without_catalog": history_without_catalog,
    }
