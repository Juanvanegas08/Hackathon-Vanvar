"""Phone number helpers for Twilio voice flows."""

from __future__ import annotations

import re


def normalize_phone(value: str, *, default_region: str = "57") -> str:
    """Normalize a phone string to E.164 when possible.

    Colombian 10-digit mobiles starting with 3 become +57...
    Numbers already in E.164 are returned with a leading +.
    """
    raw = (value or "").strip()
    if not raw:
        raise ValueError("El teléfono es obligatorio")

    digits = re.sub(r"\D", "", raw)
    if not digits:
        raise ValueError("El teléfono no es válido")

    if raw.startswith("+") and len(digits) >= 10:
        return f"+{digits}"

    if len(digits) == 10 and digits.startswith("3"):
        return f"+{default_region}{digits}"

    if digits.startswith(default_region) and len(digits) >= 12:
        return f"+{digits}"

    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"

    # Colombian landline-style 10 digits starting with 60x area codes
    if len(digits) == 10 and digits.startswith("6"):
        return f"+{default_region}{digits}"

    if len(digits) >= 10:
        return f"+{digits}"

    raise ValueError(
        "Teléfono inválido. Usa un móvil colombiano de 10 dígitos "
        "(ej. 3001234567) o formato internacional (ej. +573001234567)."
    )


def phones_match(left: str | None, right: str | None) -> bool:
    """Return True when both phones normalize to the same E.164 value."""
    if not left or not right:
        return False
    try:
        return normalize_phone(left) == normalize_phone(right)
    except ValueError:
        return False
