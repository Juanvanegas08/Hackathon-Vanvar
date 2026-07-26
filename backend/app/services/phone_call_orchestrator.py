"""Product orchestration for phone call requests (now / schedule)."""

from __future__ import annotations

from datetime import UTC, datetime

from twilio.base.exceptions import TwilioRestException

from app.core.exceptions import ConfigurationError, ValidationBusinessError
from app.models.lead import CanalOrigen, Lead
from app.models.scheduled_call import ScheduledPhoneCall
from app.services.identity_service import IdentityService
from app.services.lead_service import LeadService
from app.services.scheduled_call_service import ScheduledCallService
from app.services.twilio_call_service import TwilioCallService
from app.utils.phone import normalize_phone, phone_last4, resolve_callable_phone


class PhoneCallOrchestrator:
    """Create/resolve leads and start or schedule Twilio outbound calls."""

    def __init__(
        self,
        *,
        identity_service: IdentityService,
        lead_service: LeadService,
        twilio_call_service: TwilioCallService,
        scheduled_call_service: ScheduledCallService,
    ) -> None:
        self._identity = identity_service
        self._leads = lead_service
        self._twilio = twilio_call_service
        self._scheduled = scheduled_call_service

    def lookup_for_call(
        self,
        *,
        document_type: str,
        document_number: str,
    ) -> dict:
        """Resolve whether a document already has a callable phone in the DB."""
        existing = self._identity.get_lead_by_document(
            document_type=document_type,
            document_number=document_number,
        )
        if existing is None:
            return {
                "known_lead": False,
                "has_phone": False,
                "nombre": None,
                "phone_last4": None,
                "message": (
                    "No encontramos ese documento. Ingresa tu nombre y celular "
                    "para continuar."
                ),
            }

        stored_phone = resolve_callable_phone(existing.telefono)
        last4 = phone_last4(stored_phone) or phone_last4(existing.telefono)
        has_phone = stored_phone is not None and last4 is not None
        display_name = (existing.nombre or "").strip() or None
        if has_phone:
            return {
                "known_lead": True,
                "has_phone": True,
                "nombre": display_name,
                "phone_last4": last4,
                "message": (
                    "Encontramos tu documento. Confirma si te llamamos al número "
                    f"terminado en {last4}."
                ),
            }
        return {
            "known_lead": True,
            "has_phone": False,
            "nombre": display_name,
            "phone_last4": None,
            "message": (
                "Encontramos tu documento, pero no hay un celular completo "
                "registrado. Ingresa el número para continuar."
            ),
        }

    def request_call(
        self,
        *,
        mode: str,
        document_type: str,
        document_number: str,
        data_consent: bool,
        confirm_stored_phone: bool = False,
        phone: str | None = None,
        country_code: str = "57",
        nombre: str | None = None,
        scheduled_at: datetime | None = None,
    ) -> dict:
        if not data_consent:
            raise ValidationBusinessError(
                "Se requiere consentimiento de datos para iniciar la llamada."
            )

        lead, identity_context = self._identity.create_lead_from_identity(
            document_type=document_type,
            document_number=document_number,
            data_consent=True,
        )

        if confirm_stored_phone:
            e164, display_name = self._resolve_confirmed_phone(
                lead,
                nombre=nombre,
            )
        else:
            display_name = " ".join((nombre or "").split())
            if len(display_name) < 2:
                raise ValidationBusinessError("El nombre es obligatorio.")
            try:
                e164 = normalize_phone(phone or "", country_code=country_code)
            except ValueError as exc:
                raise ValidationBusinessError(str(exc)) from exc

        # Persist name + phone on the lead (and identity.persons via Postgres upsert).
        lead = self._leads.apply_lead_updates(
            lead.id,
            {
                "nombre": display_name,
                "telefono": e164,
                "canal_origen": CanalOrigen.OTRO,
            },
        )

        if mode == "now":
            try:
                call_sid = self._twilio.start_outbound(lead_id=lead.id, to_phone=e164)
            except TwilioRestException as exc:
                raise ValidationBusinessError(
                    f"Twilio no pudo iniciar la llamada: {exc.msg}"
                ) from exc
            return {
                "mode": "now",
                "lead_id": lead.id,
                "phone": e164,
                "call_sid": call_sid,
                "scheduled_call_id": None,
                "scheduled_at": None,
                "status": "queued",
                "message": "Te estamos llamando ahora.",
                "identity_context": identity_context,
            }

        if mode == "schedule":
            if scheduled_at is None:
                raise ValidationBusinessError("scheduled_at es obligatorio para programar.")
            when = scheduled_at
            if when.tzinfo is None:
                when = when.replace(tzinfo=UTC)
            when = when.astimezone(UTC)
            if when <= datetime.now(UTC):
                raise ValidationBusinessError(
                    "La fecha programada debe ser en el futuro."
                )
            item = self._scheduled.schedule(
                lead_id=lead.id,
                phone=e164,
                scheduled_at=when,
            )
            return {
                "mode": "schedule",
                "lead_id": lead.id,
                "phone": e164,
                "call_sid": None,
                "scheduled_call_id": item.id,
                "scheduled_at": item.scheduled_at,
                "status": item.status.value,
                "message": "Llamada programada correctamente.",
                "identity_context": identity_context,
            }

        raise ValidationBusinessError("mode debe ser 'now' o 'schedule'.")

    def _resolve_confirmed_phone(
        self,
        lead: Lead,
        *,
        nombre: str | None,
    ) -> tuple[str, str]:
        stored = resolve_callable_phone(lead.telefono)
        if stored is None:
            raise ValidationBusinessError(
                "No hay un celular registrado para ese documento. "
                "Ingresa el número para continuar."
            )
        display_name = " ".join((nombre or lead.nombre or "").split())
        if len(display_name) < 2:
            raise ValidationBusinessError(
                "Necesitamos tu nombre para continuar con la llamada."
            )
        return stored, display_name

    def process_due_scheduled_calls(self) -> list[ScheduledPhoneCall]:
        """Claim due calls and place outbound Twilio calls."""
        claimed = self._scheduled.claim_due()
        for item in claimed:
            try:
                call_sid = self._twilio.start_outbound(
                    lead_id=item.lead_id,
                    to_phone=item.phone,
                )
                self._scheduled.mark_completed(item.id, call_sid=call_sid)
            except (ConfigurationError, Exception) as exc:  # noqa: BLE001
                self._scheduled.mark_failed(item.id, error_message=str(exc))
        return claimed
