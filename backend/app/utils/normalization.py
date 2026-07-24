"""Text and value normalization helpers for data preparation scripts."""

from __future__ import annotations

import math
import re
import unicodedata
from typing import Any

# Hackathon export stores VLR_VIVIENDA inflated by this factor.
HOUSING_VALUE_EXPORT_SCALE: float = 10_000.0
HOUSING_VALUE_PLAUSIBLE_MIN: float = 20_000_000.0
HOUSING_VALUE_PLAUSIBLE_MAX: float = 2_000_000_000.0


def strip_text(value: Any) -> str | None:
    """Trim whitespace; return None for empty values."""
    if value is None:
        return None
    # pandas/numpy NaN becomes the literal string "nan" if we str() it blindly.
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "nat", "<na>"}:
        return None
    return text


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

YES_NO_TRUE_VALUES = {
    "si",
    "sí",
    "s",
    "true",
    "1",
    "yes",
    "y",
}
YES_NO_FALSE_VALUES = {
    "no",
    "n",
    "false",
    "0",
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


def normalize_yes_no_flag(value: Any) -> bool | None:
    """Map Si/No style flags to bool; return None if unrecognized."""
    normalized = normalize_for_comparison(value)
    if normalized is None:
        return None
    if normalized in YES_NO_TRUE_VALUES:
        return True
    if normalized in YES_NO_FALSE_VALUES:
        return False
    return None


def infer_affiliation_from_periodo(periodo_afiliado: Any) -> bool:
    """Infer affiliation from PERIODO_AFILIADO in the hackathon export.

    Empty periodo correlates 1:1 with non-affiliated coded rows (PI/CHI).
    """
    return strip_text(periodo_afiliado) is not None


def normalize_age_range_label(value: Any) -> str | None:
    """Unify age-range labels like '20 - 35 años' and '20 a 35 años'."""
    text = strip_text(value)
    if text is None:
        return None
    normalized = normalize_for_comparison(text) or ""
    if "menor de 19" in normalized:
        return "Menor de 19 años"
    if "mayor de 55" in normalized:
        return "Mayor de 55 años"
    if re.search(r"20\s*[-a]\s*35", normalized):
        return "20 a 35 años"
    if re.search(r"36\s*[-a]\s*45", normalized):
        return "36 a 45 años"
    if re.search(r"46\s*[-a]\s*55", normalized):
        return "46 a 55 años"
    return text


def parse_money_value(value: Any) -> tuple[float | None, str | None]:
    """Best-effort money parsing. Returns (amount, warning)."""
    if value is None:
        return None, None
    if isinstance(value, float) and math.isnan(value):
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


def scale_housing_value(amount: float | None) -> tuple[float | None, bool, str | None]:
    """Scale over-inflated housing values from the hackathon CSV/Excel export.

    Observed pattern: raw values are ~10_000x the plausible COP price
    (median raw ~1.95e12 → ~1.95e8 after /10_000).
    """
    if amount is None:
        return None, False, None

    note: str | None = None
    scaled = float(amount)
    if scaled > HOUSING_VALUE_PLAUSIBLE_MAX:
        scaled = scaled / HOUSING_VALUE_EXPORT_SCALE
        note = f"Escalado /{int(HOUSING_VALUE_EXPORT_SCALE)} por formato de exportación"

    reliable = HOUSING_VALUE_PLAUSIBLE_MIN <= scaled <= HOUSING_VALUE_PLAUSIBLE_MAX
    if not reliable and note is None:
        note = "Valor fuera del rango plausible de vivienda (COP)"
    return scaled, reliable, note
