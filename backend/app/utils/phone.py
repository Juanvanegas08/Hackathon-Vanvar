"""Phone number helpers for Twilio voice flows."""

from __future__ import annotations

import re


def normalize_country_code(value: str | None, *, default: str = "57") -> str:
    """Return digits-only dialing country code (no '+')."""
    digits = re.sub(r"\D", "", (value or "").strip())
    if not digits:
        return default
    if len(digits) > 4:
        raise ValueError("El indicativo de país no es válido.")
    return digits


def normalize_phone(
    value: str,
    *,
    country_code: str | None = None,
    default_region: str = "57",
) -> str:
    """Normalize a phone string to E.164 when possible.

    When ``country_code`` is provided, it is combined with the national number.
    Numbers already in E.164 (leading '+') keep their full international form.
    """
    raw = (value or "").strip()
    if not raw:
        raise ValueError("El teléfono es obligatorio")

    digits = re.sub(r"\D", "", raw)
    if not digits:
        raise ValueError("El teléfono no es válido")

    if raw.startswith("+") and len(digits) >= 10:
        return f"+{digits}"

    region = normalize_country_code(country_code, default=default_region)

    # Explicit country code from the form: build E.164 from parts.
    if country_code is not None:
        national = digits.lstrip("0") or digits
        if national.startswith(region) and len(national) >= len(region) + 8:
            return f"+{national}"
        if len(national) < 7:
            raise ValueError("El número telefónico es demasiado corto.")
        return f"+{region}{national}"

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
        "Teléfono inválido. Usa un móvil de 7–10 dígitos "
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


def phone_last4(value: str | None) -> str | None:
    """Return the last 4 digits of a phone, or None when unavailable."""
    digits = re.sub(r"\D", "", (value or "").strip())
    if len(digits) < 4:
        return None
    return digits[-4:]


def resolve_callable_phone(value: str | None) -> str | None:
    """Return E.164 when ``value`` is a full phone; ignore masked last-4 stubs."""
    raw = (value or "").strip()
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    # Masked stubs from contact_points are 4 digits — not dialable.
    if len(digits) < 7:
        return None
    try:
        return normalize_phone(raw)
    except ValueError:
        return None


# Provisional hackathon allow-list: these numbers may be reassigned across persons
# when the unique (contact_type, value_hash) constraint would otherwise block upserts.
REASSIGNABLE_DEMO_PHONES = frozenset({"+573224347771"})


def is_reassignable_demo_phone(value: str | None) -> bool:
    """True when the phone may be moved to another person (demo reuse)."""
    resolved = resolve_callable_phone(value)
    return resolved in REASSIGNABLE_DEMO_PHONES if resolved else False
