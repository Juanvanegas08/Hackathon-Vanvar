"""Simulated affiliation lookup for hackathon demos."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.config import Settings, get_settings
from app.providers.affiliation_provider import MockAffiliateRecord


class MockAffiliationLookupProvider:
    """Load fictional affiliates from a local JSON file.

    This provider is explicitly a mock and must never be treated as an
    official Colsubsidio integration.
    """

    SOURCE = "mock_affiliation_service"

    def __init__(
        self,
        settings: Settings | None = None,
        path: str | Path | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._path = Path(path or self._settings.mock_affiliates_path)
        self._records = self._load()

    def lookup(
        self,
        document_type: str,
        document_number: str,
    ) -> MockAffiliateRecord | None:
        doc_type = document_type.strip().upper()
        doc_number = document_number.strip()
        for record in self._records:
            if (
                record.document_type.upper() == doc_type
                and record.document_number == doc_number
            ):
                return record
        return None

    def list_demo_identities(self) -> list[MockAffiliateRecord]:
        return list(self._records)

    def _load(self) -> list[MockAffiliateRecord]:
        if not self._path.exists():
            return []
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        return [MockAffiliateRecord.model_validate(item) for item in payload]


# Explicit alias requested by the phase specification.
mock_affiliation_service = MockAffiliationLookupProvider
