"""Process-wide in-memory store for scheduled Twilio outbound calls."""

from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock
from uuid import UUID

from app.models.scheduled_call import ScheduledCallStatus, ScheduledPhoneCall


class ScheduledCallService:
    """Store and claim due scheduled phone calls (hackathon MVP, memory-only)."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._items: dict[UUID, ScheduledPhoneCall] = {}

    def schedule(
        self,
        *,
        lead_id: UUID,
        phone: str,
        scheduled_at: datetime,
    ) -> ScheduledPhoneCall:
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=UTC)
        item = ScheduledPhoneCall(
            lead_id=lead_id,
            phone=phone,
            scheduled_at=scheduled_at.astimezone(UTC),
        )
        with self._lock:
            self._items[item.id] = item
        return item

    def get(self, call_id: UUID) -> ScheduledPhoneCall | None:
        with self._lock:
            return self._items.get(call_id)

    def list_all(self) -> list[ScheduledPhoneCall]:
        with self._lock:
            return list(self._items.values())

    def claim_due(self, *, now: datetime | None = None) -> list[ScheduledPhoneCall]:
        """Atomically mark due pending calls as in_progress and return them."""
        moment = now or datetime.now(UTC)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=UTC)
        claimed: list[ScheduledPhoneCall] = []
        with self._lock:
            for item in self._items.values():
                if (
                    item.status == ScheduledCallStatus.PENDING
                    and item.scheduled_at <= moment
                ):
                    updated = item.model_copy(
                        update={
                            "status": ScheduledCallStatus.IN_PROGRESS,
                            "updated_at": datetime.now(UTC),
                        }
                    )
                    self._items[item.id] = updated
                    claimed.append(updated)
        return claimed

    def mark_completed(self, call_id: UUID, *, call_sid: str | None = None) -> None:
        with self._lock:
            item = self._items.get(call_id)
            if item is None:
                return
            self._items[call_id] = item.model_copy(
                update={
                    "status": ScheduledCallStatus.COMPLETED,
                    "call_sid": call_sid or item.call_sid,
                    "updated_at": datetime.now(UTC),
                }
            )

    def mark_failed(self, call_id: UUID, *, error_message: str) -> None:
        with self._lock:
            item = self._items.get(call_id)
            if item is None:
                return
            self._items[call_id] = item.model_copy(
                update={
                    "status": ScheduledCallStatus.FAILED,
                    "error_message": error_message[:500],
                    "updated_at": datetime.now(UTC),
                }
            )
