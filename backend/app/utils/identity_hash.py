"""Deterministic hashing helpers for document identifiers."""

from __future__ import annotations

import hashlib
import hmac
import re


def normalize_document_number(document_number: str) -> str:
    """Normalize a document number for hashing and comparison."""
    return re.sub(r"\D+", "", (document_number or "").strip())


def hash_identifier(
    *,
    document_type: str,
    document_number: str,
    country_code: str = "CO",
    pepper: str = "",
) -> str:
    """Return a stable HMAC-SHA256 hash for a person identifier."""
    normalized = normalize_document_number(document_number)
    payload = (
        f"{(document_type or '').strip().upper()}|"
        f"{(country_code or 'CO').strip().upper()}|"
        f"{normalized}"
    )
    digest = hmac.new(
        (pepper or "casalista-dev-pepper").encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest


def mask_document_last_four(document_number: str) -> str | None:
    normalized = normalize_document_number(document_number)
    if not normalized:
        return None
    return normalized[-4:]
