"""Text and value normalization helpers for data preparation scripts."""

from __future__ import annotations

import re
import unicodedata
from typing import Any


def strip_text(value: Any) -> str | None:
    """Trim whitespace; return None for empty values."""
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def normalize_for_comparison(value: Any) -> str | None:
    """Lowercase, strip accents and collapse spaces for comparison only."""
    text = strip_text(value)
    if text is None:
        return None
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    collapsed = re.sub(r"\s+", " ", without_accents).strip().lower()
    return collapsed or None


AFFILIATION_TRUE_VALUES = {
    "si",
    "sí",
    "s",
    "true",
    "1",
    "afiliado",
    "afiliada",
    "afiliado(a)",
    "afiliado a",
    "yes",
    "y",
}
AFFILIATION_FALSE_VALUES = {
    "no",
    "n",
    "false",
    "0",
    "no afiliado",
    "no afiliada",
    "no afiliado(a)",
    "independiente",
}
AFFILIATION_AMBIGUOUS_VALUES = {
    "estuvo afiliado",
    "estuvo afiliada",
    "estuvo afiliado(a)",
    "grupo_familiar",
    "grupo familiar",
}


def normalize_affiliation_flag(value: Any) -> bool | None:
    """Map common affiliation labels to bool; return None if ambiguous."""
    normalized = normalize_for_comparison(value)
    if normalized is None:
        return None
    if normalized in AFFILIATION_AMBIGUOUS_VALUES:
        return None
    if normalized in AFFILIATION_TRUE_VALUES:
        return True
    if normalized in AFFILIATION_FALSE_VALUES:
        return False
    if "no afiliad" in normalized:
        return False
    if normalized.startswith("afiliad") and "estuvo" not in normalized:
        return True
    return None


def parse_money_value(value: Any) -> tuple[float | None, str | None]:
    """Best-effort money parsing. Returns (amount, warning)."""
    if value is None:
        return None, None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value), None

    text = strip_text(value)
    if text is None:
        return None, None

    cleaned = text.replace("$", "").replace("COP", "").replace("cop", "").strip()
    cleaned = cleaned.replace(" ", "")

    # Colombian-style thousands with dots and decimal comma: 1.250.000,50
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", cleaned):
        cleaned = cleaned.replace(".", "").replace(",", ".")
    # US-style thousands with commas: 1,250,000.50
    elif re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", cleaned):
        cleaned = cleaned.replace(",", "")
    else:
        cleaned = cleaned.replace(",", ".")

    try:
        return float(cleaned), None
    except ValueError:
        return None, f"No se pudo interpretar el valor monetario: {text}"
