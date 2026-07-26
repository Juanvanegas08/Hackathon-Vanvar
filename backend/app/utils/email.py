"""Email helpers for demo-safe persistence and API responses."""

from __future__ import annotations

from email_validator import EmailNotValidError, validate_email


def sanitize_optional_email(value: object) -> str | None:
    """Return a validated email, or None if missing/invalid (e.g. .local demos)."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        result = validate_email(text, check_deliverability=False)
    except EmailNotValidError:
        return None
    return result.normalized
