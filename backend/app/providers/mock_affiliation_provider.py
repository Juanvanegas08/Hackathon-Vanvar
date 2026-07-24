"""Simulated affiliation lookup for hackathon demos."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.config import Settings, get_settings
from app.providers.affiliation_provider import MockAffiliateRecord


class MockAffiliationLookupProvider:
    """Load fictional affiliates from local JSON file(s).

    This provider is explicitly a mock and must never be treated as an
    official Colsubsidio integration.

    Loads curated demos from MOCK_AFFILIATES_PATH and, when present, the
    historical synthetic cohort from MOCK_AFFILIATES_HISTORICAL_PATH.
    Curated demos win on document collisions.
    """

    SOURCE = "mock_affiliation_service"

    def __init__(
        self,
        settings: Settings | None = None,
        path: str | Path | None = None,
        historical_path: str | Path | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._path = Path(path or self._settings.mock_affiliates_path)
        self._historical_path = Path(
            historical_path
            if historical_path is not None
            else self._settings.mock_affiliates_historical_path
        )
        self._records = self._load()
        self._by_key = {
            (record.document_type.upper(), record.document_number): record
            for record in self._records
        }

    def lookup(
        self,
        document_type: str,
        document_number: str,
    ) -> MockAffiliateRecord | None:
        doc_type = document_type.strip().upper()
        doc_number = document_number.strip()
        return self._by_key.get((doc_type, doc_number))

    def list_demo_identities(self) -> list[MockAffiliateRecord]:
        return list(self._records)

    def _load_file(self, path: Path) -> list[MockAffiliateRecord]:
        if not path.exists():
            return []
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            return []
        return [MockAffiliateRecord.model_validate(item) for item in payload]

    def _load(self) -> list[MockAffiliateRecord]:
        curated = self._load_file(self._path)
        historical = self._load_file(self._historical_path)
        if not historical:
            return curated

        curated_keys = {
            (row.document_type.upper(), row.document_number) for row in curated
        }
        merged = list(curated)
        for row in historical:
            key = (row.document_type.upper(), row.document_number)
            if key not in curated_keys:
                merged.append(row)
        return merged


# Explicit alias requested by the phase specification.
mock_affiliation_service = MockAffiliationLookupProvider
