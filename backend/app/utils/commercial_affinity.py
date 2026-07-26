"""Commercial housing-affinity classification for the advisor queue."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class AffinityBand(StrEnum):
    """Commercial band derived from top-project compatibility score."""

    LISTO = "listo"
    POR_EVALUAR = "por_evaluar"
    BAJA_AFINIDAD = "baja_afinidad"


def classify_affinity(score: float | int | None) -> AffinityBand | None:
    """Map a 0–100 compatibility score to a commercial band."""
    if score is None:
        return None
    value = float(score)
    if value >= 70:
        return AffinityBand.LISTO
    if value >= 30:
        return AffinityBand.POR_EVALUAR
    return AffinityBand.BAJA_AFINIDAD


def build_commercial_snapshot(
    *,
    affinity_percent: float | int,
    top_project_id: str | None,
    top_project_name: str | None,
    evaluated_at: datetime | None = None,
) -> dict[str, Any]:
    """Build the JSON payload stored under profile commercial.* keys."""
    percent = round(float(affinity_percent), 2)
    band = classify_affinity(percent)
    return {
        "affinity_percent": percent,
        "affinity_band": band.value if band else None,
        "top_project_id": top_project_id,
        "top_project_name": top_project_name,
        "evaluated_at": (evaluated_at or datetime.now(UTC)).isoformat(),
    }


def parse_commercial_snapshot(raw: object) -> dict[str, Any] | None:
    """Normalize a commercial snapshot from profile JSON."""
    if not isinstance(raw, dict):
        return None
    percent = raw.get("affinity_percent")
    if not isinstance(percent, (int, float)):
        return None
    band = classify_affinity(percent)
    return {
        "affinity_percent": round(float(percent), 2),
        "affinity_band": (
            raw.get("affinity_band")
            if isinstance(raw.get("affinity_band"), str)
            else (band.value if band else None)
        ),
        "top_project_id": (
            str(raw["top_project_id"]) if raw.get("top_project_id") is not None else None
        ),
        "top_project_name": (
            str(raw["top_project_name"])
            if raw.get("top_project_name") is not None
            else None
        ),
        "evaluated_at": raw.get("evaluated_at"),
    }
