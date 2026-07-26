"""PostgreSQL-backed lead repository using identity + leads schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError
from app.db.models.identity import Consent, ContactPoint, Person, PersonIdentifier
from app.db.models.leads import (
    Lead as LeadRow,
    LeadEvent,
    LeadFieldMetadata,
    LeadProfile,
)
from app.db.sync_engine import get_sync_session_factory, sync_session_scope
from app.models.lead import DataSource, DocumentType, IdentityStatus, Lead
from app.repositories.lead_mapping import (
    build_profile_columns,
    domain_lead_from_rows,
    domain_status_to_db,
    split_display_name,
)
from app.services.profile_persistence_service import ProfilePersistenceService
from app.utils.identity_hash import (
    candidate_identifier_hashes,
    hash_identifier,
    mask_document_last_four,
    normalize_document_number,
)
from app.utils.phone import is_reassignable_demo_phone, resolve_callable_phone


class PostgresLeadRepository:
    """Persist leads/profiles in PostgreSQL (identity + leads domains)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._profiles = ProfilePersistenceService(self._settings)
        factory = get_sync_session_factory(self._settings)
        if factory is None:
            raise RuntimeError(
                "DATABASE_ENABLED/DATABASE_URL required for PostgresLeadRepository"
            )

    def create(self, lead: Lead) -> Lead:
        with sync_session_scope(self._settings) as session:
            return self._upsert_full(session, lead, create_if_missing=True)

    def get_by_id(self, lead_id: UUID) -> Lead | None:
        with sync_session_scope(self._settings) as session:
            row = session.get(LeadRow, lead_id)
            if row is None:
                return None
            return self._to_domain(session, row)

    def list_all(self) -> list[Lead]:
        with sync_session_scope(self._settings) as session:
            rows = session.scalars(select(LeadRow).order_by(LeadRow.created_at.desc())).all()
            return [self._to_domain(session, row) for row in rows]

    def update(self, lead: Lead) -> Lead:
        with sync_session_scope(self._settings) as session:
            existing = session.get(LeadRow, lead.id)
            if existing is None:
                raise NotFoundError(f"Lead {lead.id} no encontrado")
            return self._upsert_full(session, lead, create_if_missing=False)

    def delete(self, lead_id: UUID) -> bool:
        with sync_session_scope(self._settings) as session:
            row = session.get(LeadRow, lead_id)
            if row is None:
                return False
            session.delete(row)
            return True

    def get_by_document(
        self,
        document_type: str,
        document_number: str,
        *,
        country_code: str = "CO",
    ) -> Lead | None:
        doc_type = document_type.strip().upper()
        doc_number = normalize_document_number(document_number)
        country = (country_code or "CO").strip().upper()
        hashes = candidate_identifier_hashes(
            document_type=doc_type,
            document_number=doc_number,
            country_code=country,
            pepper=self._settings.identity_hash_pepper,
        )
        with sync_session_scope(self._settings) as session:
            identifier = session.scalar(
                select(PersonIdentifier).where(
                    PersonIdentifier.identifier_type == doc_type,
                    PersonIdentifier.country_code == country,
                    PersonIdentifier.identifier_hash.in_(hashes),
                )
            )
            if identifier is None:
                return None
            lead_row = session.scalar(
                select(LeadRow)
                .where(LeadRow.person_id == identifier.person_id)
                .order_by(LeadRow.created_at.desc())
                .limit(1)
            )
            if lead_row is None:
                # Historical synthetic persons exist in identity.* without a lead.
                # Attach a lead so phone/identity flows can reuse name + phone.
                lead_row = self._attach_lead_for_person(
                    session,
                    person_id=identifier.person_id,
                    document_type=doc_type,
                    document_number=doc_number
                    or normalize_document_number(
                        identifier.identifier_ciphertext or ""
                    ),
                )
            return self._to_domain(
                session,
                lead_row,
                document_type=doc_type,
                document_number=doc_number
                or normalize_document_number(identifier.identifier_ciphertext or ""),
            )

    def save_profile(self, lead: Lead) -> Lead:
        """Upsert the full profile document in PostgreSQL after the conversation."""
        return self.update(lead) if self.get_by_id(lead.id) else self.create(lead)

    def reset_profile(self, lead: Lead) -> Lead:
        """Wipe profile columns, field metadata and recommendation runs for the lead."""
        with sync_session_scope(self._settings) as session:
            existing = session.get(LeadRow, lead.id)
            if existing is None:
                raise NotFoundError(f"Lead {lead.id} no encontrado")
            self._clear_recommendation_runs(session, lead.id)
            self._clear_field_metadata(session, lead.id)
            self._clear_person_contacts(session, existing.person_id)
            return self._upsert_full(session, lead, create_if_missing=False)

    def _clear_person_contacts(self, session: Session, person_id: UUID) -> None:
        contacts = session.scalars(
            select(ContactPoint).where(ContactPoint.person_id == person_id)
        ).all()
        for contact in contacts:
            session.delete(contact)

    def _clear_field_metadata(self, session: Session, lead_id: UUID) -> None:
        rows = session.scalars(
            select(LeadFieldMetadata).where(LeadFieldMetadata.lead_id == lead_id)
        ).all()
        for row in rows:
            session.delete(row)

    def _clear_recommendation_runs(self, session: Session, lead_id: UUID) -> None:
        try:
            from app.db.models.recommendations import (
                RecommendationFactor,
                RecommendationFeedback,
                RecommendationItem,
                RecommendationRun,
            )
        except Exception:  # noqa: BLE001
            return

        runs = session.scalars(
            select(RecommendationRun).where(RecommendationRun.lead_id == lead_id)
        ).all()
        for run in runs:
            items = session.scalars(
                select(RecommendationItem).where(
                    RecommendationItem.recommendation_run_id == run.id
                )
            ).all()
            for item in items:
                factors = session.scalars(
                    select(RecommendationFactor).where(
                        RecommendationFactor.recommendation_item_id == item.id
                    )
                ).all()
                for factor in factors:
                    session.delete(factor)
                feedbacks = session.scalars(
                    select(RecommendationFeedback).where(
                        RecommendationFeedback.recommendation_item_id == item.id
                    )
                ).all()
                for feedback in feedbacks:
                    session.delete(feedback)
                session.delete(item)
            session.delete(run)

    def _upsert_full(
        self,
        session: Session,
        lead: Lead,
        *,
        create_if_missing: bool,
    ) -> Lead:
        now = datetime.now(UTC)
        document = self._profiles.build_document(lead)
        first_name, last_name, display_name = split_display_name(lead.nombre)

        lead_row = session.get(LeadRow, lead.id)
        if lead_row is None:
            if not create_if_missing:
                raise NotFoundError(f"Lead {lead.id} no encontrado")
            person = Person(
                id=uuid4(),
                first_name=first_name,
                last_name=last_name,
                display_name=display_name,
                identity_status=(
                    lead.identity_status.value
                    if hasattr(lead.identity_status, "value")
                    else str(lead.identity_status)
                ),
                is_demo=bool(lead.demo_mode),
            )
            session.add(person)
            session.flush()

            if lead.document_type and lead.document_number:
                session.add(
                    PersonIdentifier(
                        id=uuid4(),
                        person_id=person.id,
                        identifier_type=str(lead.document_type.value
                            if hasattr(lead.document_type, "value")
                            else lead.document_type).upper(),
                        identifier_hash=hash_identifier(
                            document_type=str(
                                lead.document_type.value
                                if hasattr(lead.document_type, "value")
                                else lead.document_type
                            ),
                            document_number=lead.document_number,
                            pepper=self._settings.identity_hash_pepper,
                        ),
                        identifier_last_four=mask_document_last_four(
                            lead.document_number
                        ),
                        country_code="CO",
                        is_primary=True,
                        is_verified=bool(lead.identity_verified),
                        verified_at=now if lead.identity_verified else None,
                    )
                )

            self._upsert_contacts(session, person.id, lead)

            if lead.data_consent is not None:
                session.add(
                    Consent(
                        id=uuid4(),
                        person_id=person.id,
                        consent_type="data_processing",
                        granted=bool(lead.data_consent),
                        version="v1",
                        channel="voice_app",
                        granted_at=(
                            (lead.data_consent_at or now) if lead.data_consent else None
                        ),
                        metadata_={"source": "identity_flow"},
                    )
                )

            lead_row = LeadRow(
                id=lead.id,
                person_id=person.id,
                known_lead=bool(lead.known_lead),
                identity_status=(
                    lead.identity_status.value
                    if hasattr(lead.identity_status, "value")
                    else str(lead.identity_status)
                ),
                status=domain_status_to_db(lead.estado_lead),
                current_profile_version=1,
            )
            session.add(lead_row)
            session.flush()
            session.add(
                LeadEvent(
                    id=uuid4(),
                    lead_id=lead.id,
                    event_type="lead_created",
                    actor_type="system",
                    metadata_={"source": "postgres_lead_repository"},
                    occurred_at=now,
                )
            )
        else:
            person = session.get(Person, lead_row.person_id)
            if person is not None:
                person.first_name = first_name
                person.last_name = last_name
                person.display_name = display_name
                person.identity_status = (
                    lead.identity_status.value
                    if hasattr(lead.identity_status, "value")
                    else str(lead.identity_status)
                )
                self._upsert_contacts(session, person.id, lead)
            lead_row.known_lead = bool(lead.known_lead)
            lead_row.identity_status = (
                lead.identity_status.value
                if hasattr(lead.identity_status, "value")
                else str(lead.identity_status)
            )
            lead_row.status = domain_status_to_db(lead.estado_lead)
            lead_row.current_profile_version = int(lead_row.current_profile_version or 1) + 1

        profile = session.get(LeadProfile, lead.id)
        columns = build_profile_columns(lead, document)
        if profile is None:
            profile = LeadProfile(lead_id=lead.id, version=1, **columns)
            session.add(profile)
        else:
            for key, value in columns.items():
                setattr(profile, key, value)
            profile.version = int(profile.version or 1) + 1

        self._upsert_field_metadata(session, lead, now)
        session.add(
            LeadEvent(
                id=uuid4(),
                lead_id=lead.id,
                event_type="profile_upserted",
                actor_type="system",
                metadata_={
                    "profile_completeness": columns["profile_completeness"],
                    "version": profile.version,
                },
                occurred_at=now,
            )
        )
        session.flush()
        return self._to_domain(session, lead_row)

    def _upsert_contacts(self, session: Session, person_id: UUID, lead: Lead) -> None:
        contacts: list[tuple[str, str | None]] = [
            ("phone", lead.telefono),
            ("email", str(lead.correo) if lead.correo else None),
        ]
        for contact_type, raw_value in contacts:
            if not raw_value:
                continue
            value = raw_value.strip().lower()
            # Contact hashes are not document numbers; keep a stable digest.
            from hashlib import sha256

            value_hash = sha256(
                f"{contact_type}|{value}|{self._settings.identity_hash_pepper}".encode()
            ).hexdigest()
            existing = session.scalar(
                select(ContactPoint).where(
                    ContactPoint.person_id == person_id,
                    ContactPoint.contact_type == contact_type,
                )
            )
            masked = value[-4:] if contact_type == "phone" else value
            # Global uniqueness: (contact_type, value_hash).
            collision = session.scalar(
                select(ContactPoint).where(
                    ContactPoint.contact_type == contact_type,
                    ContactPoint.value_hash == value_hash,
                )
            )
            can_reassign = contact_type == "phone" and is_reassignable_demo_phone(
                raw_value
            )

            if (
                collision is not None
                and collision.person_id != person_id
                and can_reassign
            ):
                # Provisional demo reuse: move the shared phone to this person.
                if existing is not None and existing.id != collision.id:
                    session.delete(existing)
                    session.flush()
                collision.person_id = person_id
                collision.masked_value = masked
                collision.is_primary = True
                continue

            if existing is None:
                if collision is not None:
                    # Another person already owns this contact hash.
                    continue
                session.add(
                    ContactPoint(
                        id=uuid4(),
                        person_id=person_id,
                        contact_type=contact_type,
                        value_hash=value_hash,
                        masked_value=masked,
                        is_primary=True,
                    )
                )
                continue

            if existing.value_hash == value_hash:
                existing.masked_value = masked
                existing.is_primary = True
                continue

            if collision is not None and collision.id != existing.id:
                continue

            existing.value_hash = value_hash
            existing.masked_value = masked
            existing.is_primary = True

    def _upsert_field_metadata(
        self,
        session: Session,
        lead: Lead,
        now: datetime,
    ) -> None:
        for field, meta in lead.field_metadata.items():
            row = session.get(LeadFieldMetadata, (lead.id, field))
            payload: dict[str, Any] = {
                "source": (
                    meta.source.value if isinstance(meta.source, DataSource) else str(meta.source)
                ),
                "previous_value": meta.previous_value,
            }
            if row is None:
                session.add(
                    LeadFieldMetadata(
                        lead_id=lead.id,
                        field_name=field,
                        confirmed=bool(meta.confirmed),
                        requires_confirmation=bool(meta.requires_confirmation),
                        captured_at=meta.updated_at or now,
                        confirmed_at=now if meta.confirmed else None,
                        metadata_=payload,
                    )
                )
            else:
                row.confirmed = bool(meta.confirmed)
                row.requires_confirmation = bool(meta.requires_confirmation)
                row.confirmed_at = now if meta.confirmed else row.confirmed_at
                row.metadata_ = payload

    def _attach_lead_for_person(
        self,
        session: Session,
        *,
        person_id: UUID,
        document_type: str,
        document_number: str,
    ) -> LeadRow:
        now = datetime.now(UTC)
        person = session.get(Person, person_id)
        phone = session.scalar(
            select(ContactPoint).where(
                ContactPoint.person_id == person_id,
                ContactPoint.contact_type == "phone",
                ContactPoint.is_primary.is_(True),
            )
        )
        email = session.scalar(
            select(ContactPoint).where(
                ContactPoint.person_id == person_id,
                ContactPoint.contact_type == "email",
                ContactPoint.is_primary.is_(True),
            )
        )
        phone_value = self._contact_raw_value(phone)
        email_value = self._contact_raw_value(email)
        display_name = person.display_name if person else None
        raw_status = (
            (person.identity_status if person and person.identity_status else None)
            or IdentityStatus.KNOWN_AFFILIATE.value
        )
        try:
            identity_status = IdentityStatus(raw_status)
        except ValueError:
            identity_status = IdentityStatus.KNOWN_AFFILIATE
        try:
            doc_type = DocumentType(document_type)
        except ValueError:
            doc_type = DocumentType.CC

        lead_row = LeadRow(
            id=uuid4(),
            person_id=person_id,
            known_lead=True,
            identity_status=identity_status.value,
            status="new",
            current_profile_version=1,
        )
        session.add(lead_row)
        session.flush()

        draft = Lead(
            id=lead_row.id,
            nombre=display_name,
            telefono=resolve_callable_phone(phone_value) or phone_value,
            correo=email_value,
            document_type=doc_type,
            document_number=document_number,
            known_lead=True,
            identity_status=identity_status,
            demo_mode=bool(person.is_demo) if person else True,
            profile_source=DataSource.HISTORICAL_DATA,
        )
        document = self._profiles.build_document(draft)
        columns = build_profile_columns(draft, document)
        session.add(LeadProfile(lead_id=lead_row.id, version=1, **columns))
        session.add(
            LeadEvent(
                id=uuid4(),
                lead_id=lead_row.id,
                event_type="lead_attached_from_person",
                actor_type="system",
                metadata_={
                    "source": "postgres_lead_repository",
                    "person_id": str(person_id),
                },
                occurred_at=now,
            )
        )
        session.flush()
        return lead_row

    @staticmethod
    def _contact_raw_value(contact: ContactPoint | None) -> str | None:
        if contact is None:
            return None
        raw = (contact.value_ciphertext or contact.masked_value or "").strip()
        return raw or None

    def _to_domain(
        self,
        session: Session,
        lead_row: LeadRow,
        *,
        document_type: str | None = None,
        document_number: str | None = None,
    ) -> Lead:
        person = session.get(Person, lead_row.person_id)
        profile = session.get(LeadProfile, lead_row.id)
        identifier = session.scalar(
            select(PersonIdentifier)
            .where(
                PersonIdentifier.person_id == lead_row.person_id,
                PersonIdentifier.is_primary.is_(True),
            )
            .limit(1)
        )
        phone = session.scalar(
            select(ContactPoint).where(
                ContactPoint.person_id == lead_row.person_id,
                ContactPoint.contact_type == "phone",
                ContactPoint.is_primary.is_(True),
            )
        )
        email = session.scalar(
            select(ContactPoint).where(
                ContactPoint.person_id == lead_row.person_id,
                ContactPoint.contact_type == "email",
                ContactPoint.is_primary.is_(True),
            )
        )
        phone_value = self._contact_raw_value(phone)
        email_value = self._contact_raw_value(email)
        return domain_lead_from_rows(
            lead_id=lead_row.id,
            person_display_name=person.display_name if person else None,
            lead_known=bool(lead_row.known_lead),
            lead_identity_status=lead_row.identity_status,
            lead_status=lead_row.status,
            profile=profile,
            document_type=document_type
            or (identifier.identifier_type if identifier else None),
            document_number=(
                document_number
                or (
                    normalize_document_number(identifier.identifier_ciphertext)
                    if identifier and identifier.identifier_ciphertext
                    else None
                )
            ),
            phone=resolve_callable_phone(phone_value) or phone_value,
            email=email_value,
        )
