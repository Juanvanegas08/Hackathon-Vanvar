"""Identity lookup and known-lead prefill orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.exceptions import InvalidSmmlvError, ValidationBusinessError
from app.models.lead import (
    AffiliationCategory,
    DataSource,
    DocumentType,
    FieldProvenance,
    IdentityStatus,
    Lead,
)
from app.providers.affiliation_provider import AffiliationLookupProvider, MockAffiliateRecord
from app.providers.mock_affiliation_provider import MockAffiliationLookupProvider
from app.repositories.lead_repository import LeadRepository
from app.services.affiliation_service import AffiliationService


class IdentityService:
    """Coordinate mock identity lookup and lead prefill flows."""

    CONFIRMABLE_DEFAULTS = ("salario_mensual", "personas_a_cargo")

    def __init__(
        self,
        repository: LeadRepository,
        provider: AffiliationLookupProvider | None = None,
        affiliation_service: AffiliationService | None = None,
        question_service: object | None = None,
    ) -> None:
        self._repository = repository
        self._provider = provider or MockAffiliationLookupProvider()
        self._affiliation = affiliation_service or AffiliationService()
        _ = question_service

    def lookup(self, document_type: str, document_number: str) -> dict[str, Any]:
        """Lookup an identity without creating a lead."""
        record = self._provider.lookup(document_type, document_number)
        if record is None:
            return {
                "match_status": IdentityStatus.NEW_LEAD.value,
                "known_lead": False,
                "identity_verified": False,
                "profile_source": MockAffiliationLookupProvider.SOURCE,
                "prefilled_profile": {},
                "prefilled_fields": [],
                "fields_to_confirm": [],
                "consent_required": True,
                "demo_mode": True,
            }

        status = self._status_from_record(record)
        profile, prefilled_fields, fields_to_confirm = self._build_prefilled(record)
        return {
            "match_status": status.value,
            "known_lead": True,
            "identity_verified": False,
            "profile_source": MockAffiliationLookupProvider.SOURCE,
            "prefilled_profile": profile,
            "prefilled_fields": prefilled_fields,
            "fields_to_confirm": fields_to_confirm,
            "consent_required": True,
            "demo_mode": True,
        }

    def create_lead_from_identity(
        self,
        *,
        document_type: str,
        document_number: str,
        data_consent: bool,
    ) -> tuple[Lead, dict[str, Any]]:
        """Create a lead from a mock identity lookup."""
        now = datetime.now(UTC)
        doc_type = DocumentType(document_type.upper())
        record = self._provider.lookup(document_type, document_number)

        lead = Lead(
            document_type=doc_type,
            document_number=document_number.strip(),
            data_consent=data_consent,
            data_consent_at=now if data_consent else None,
            consentimiento=True if data_consent else None,
            identity_lookup_at=now,
            identity_verified=False,
            demo_mode=True,
            profile_source=DataSource.MOCK_AFFILIATION_SERVICE,
        )

        if record is None:
            lead = lead.apply_partial_update(
                {
                    "known_lead": False,
                    "identity_status": IdentityStatus.NEW_LEAD,
                }
            )
            created = self._repository.create(lead)
            context = {
                "known_lead": False,
                "identity_status": IdentityStatus.NEW_LEAD.value,
                "identity_verified": False,
                "demo_mode": True,
            }
            return created, context

        if not data_consent:
            lead = lead.apply_partial_update(
                {
                    "known_lead": True,
                    "identity_status": self._status_from_record(record),
                    "nombre": f"{record.first_name} {record.last_name}".strip(),
                }
            )
            # Without consent we only keep non-sensitive identity labels.
            created = self._repository.create(lead)
            context = {
                "known_lead": True,
                "identity_status": created.identity_status.value,
                "identity_verified": False,
                "demo_mode": True,
                "warning": "Sin consentimiento no se precargó información financiera.",
            }
            return created, context

        profile, prefilled_fields, fields_to_confirm = self._build_prefilled(record)
        metadata = self._build_field_metadata(record, prefilled_fields, fields_to_confirm)
        updates: dict[str, Any] = {
            **profile,
            "known_lead": True,
            "identity_status": self._status_from_record(record),
            "prefilled_fields": prefilled_fields,
            "fields_to_confirm": fields_to_confirm,
            "field_metadata": metadata,
            "afiliacion_confirmada": bool(record.affiliation_confirmed),
        }
        lead = lead.apply_partial_update(updates)
        lead = self._enrich_category(lead)
        created = self._repository.create(lead)
        context = {
            "known_lead": True,
            "identity_status": created.identity_status.value,
            "identity_verified": False,
            "demo_mode": True,
            "profile_source": MockAffiliationLookupProvider.SOURCE,
        }
        return created, context

    def confirm_prefilled_data(
        self,
        lead: Lead,
        confirmations: dict[str, dict[str, Any]],
    ) -> Lead:
        """Confirm or correct prefilled fields."""
        if not confirmations:
            raise ValidationBusinessError("Debe enviar al menos una confirmación")

        allowed = set(lead.prefilled_fields) | set(lead.fields_to_confirm)
        updates: dict[str, Any] = {}
        metadata = dict(lead.field_metadata)
        pending = list(lead.fields_to_confirm)
        now = datetime.now(UTC)

        for field, payload in confirmations.items():
            if field not in allowed:
                raise ValidationBusinessError(
                    f"El campo '{field}' no está disponible para confirmación",
                    code="field_not_confirmable",
                )
            confirmed = bool(payload.get("confirmed"))
            new_value = payload.get("new_value")
            previous = getattr(lead, field, None)
            current_meta = metadata.get(field)

            if confirmed and new_value is None:
                updates[field] = previous
                metadata[field] = FieldProvenance(
                    source=(
                        current_meta.source
                        if current_meta
                        else DataSource.MOCK_AFFILIATION_SERVICE
                    ),
                    confirmed=True,
                    requires_confirmation=False,
                    updated_at=now,
                    previous_value=previous,
                )
            else:
                if new_value is None:
                    raise ValidationBusinessError(
                        f"Debe enviar new_value para corregir '{field}'",
                        code="missing_new_value",
                    )
                if isinstance(new_value, (int, float)) and float(new_value) < 0:
                    raise ValidationBusinessError(
                        "El valor no puede ser negativo",
                        code="negative_value",
                    )
                updates[field] = new_value
                metadata[field] = FieldProvenance(
                    source=DataSource.USER_DECLARED,
                    confirmed=True,
                    requires_confirmation=False,
                    updated_at=now,
                    previous_value=previous,
                )

            if field in pending:
                pending.remove(field)

        updates["fields_to_confirm"] = pending
        updates["field_metadata"] = metadata
        updated = lead.apply_partial_update(updates)
        updated = self._enrich_category(updated)
        return self._repository.update(updated)

    def list_demo_identities(self) -> list[dict[str, str]]:
        """Return safe demo identity cards."""
        items: list[dict[str, str]] = []
        for record in self._provider.list_demo_identities():
            items.append(
                {
                    "name": f"{record.first_name} {record.last_name}".strip(),
                    "document_number": record.document_number,
                    "document_type": record.document_type,
                    "scenario": record.scenario or "Escenario de demostración",
                }
            )
        return items

    def _build_prefilled(
        self,
        record: MockAffiliateRecord,
    ) -> tuple[dict[str, Any], list[str], list[str]]:
        profile: dict[str, Any] = {
            "nombre": f"{record.first_name} {record.last_name}".strip(),
            "afiliado": record.affiliated,
            "telefono": record.phone,
            "correo": record.email,
            "empresa": record.company,
            "salario_mensual": record.reported_salary,
            "personas_a_cargo": record.dependents,
            "beneficiarios_registrados": record.beneficiaries_registered,
        }
        if record.affiliation_category in {"A", "B", "C", "D"}:
            profile["categoria_afiliacion"] = AffiliationCategory(
                record.affiliation_category
            )

        prefilled_fields = [
            key for key, value in profile.items() if value is not None
        ]
        fields_to_confirm = [
            field
            for field in self.CONFIRMABLE_DEFAULTS
            if field in prefilled_fields
        ]
        if not record.affiliation_confirmed and "afiliado" in prefilled_fields:
            fields_to_confirm.append("afiliado")
        return profile, prefilled_fields, fields_to_confirm

    def _build_field_metadata(
        self,
        record: MockAffiliateRecord,
        prefilled_fields: list[str],
        fields_to_confirm: list[str],
    ) -> dict[str, FieldProvenance]:
        now = datetime.now(UTC)
        metadata: dict[str, FieldProvenance] = {}
        for field in prefilled_fields:
            source = DataSource.MOCK_AFFILIATION_SERVICE
            if field == "salario_mensual":
                source = DataSource.EMPLOYER_REPORT
            requires = field in fields_to_confirm
            metadata[field] = FieldProvenance(
                source=source,
                confirmed=bool(record.affiliation_confirmed) and not requires,
                requires_confirmation=requires,
                updated_at=now,
            )
        return metadata

    @staticmethod
    def _status_from_record(record: MockAffiliateRecord) -> IdentityStatus:
        if not record.affiliation_confirmed:
            return IdentityStatus.IDENTITY_NOT_VERIFIED
        if record.affiliated:
            return IdentityStatus.KNOWN_AFFILIATE
        return IdentityStatus.KNOWN_NON_AFFILIATE

    def _enrich_category(self, lead: Lead) -> Lead:
        try:
            result = self._affiliation.calculate_category(
                afiliado=lead.afiliado,
                salario_mensual=lead.salario_mensual,
                afiliacion_confirmada=lead.afiliacion_confirmada,
            )
            if result.categoria is not None:
                return lead.apply_partial_update(
                    {"categoria_afiliacion": result.categoria}
                )
        except (InvalidSmmlvError, ValidationBusinessError):
            return lead
        return lead
