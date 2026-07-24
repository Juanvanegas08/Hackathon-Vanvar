"""Product orchestration for phone call requests (now / schedule)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import ConfigurationError, ValidationBusinessError
from app.models.lead import CanalOrigen
from app.models.scheduled_call import ScheduledPhoneCall
from app.services.identity_service import IdentityService
from app.services.lead_service import LeadService
from app.services.scheduled_call_service import ScheduledCallService
from app.services.twilio_call_service import TwilioCallService
from app.utils.phone import normalize_phone


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

    def request_call(
        self,
        *,
        phone: str,
        mode: str,
        document_type: str,
        document_number: str,
        data_consent: bool,
        scheduled_at: datetime | None = None,
    ) -> dict:
        if not data_consent:
            raise ValidationBusinessError(
                "Se requiere consentimiento de datos para iniciar la llamada."
            )

        e164 = normalize_phone(phone)
        lead, identity_context = self._identity.create_lead_from_identity(
            document_type=document_type,
            document_number=document_number,
            data_consent=True,
        )
        lead = self._leads.apply_lead_updates(
            lead.id,
            {
                "telefono": e164,
                "canal_origen": CanalOrigen.OTRO,
            },
        )

        if mode == "now":
            call_sid = self._twilio.start_outbound(lead_id=lead.id, to_phone=e164)
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
