"""Shared helpers for lead profiling progress."""

from app.models.lead import Lead
from app.services.question_service import QuestionService


def compute_profile_progress(
    lead: Lead,
    question_service: QuestionService | None = None,
) -> int:
    """Return an approximate 0-100 progress based on complete vs pending fields."""
    questions = question_service or QuestionService()
    complete = questions.list_complete_fields(lead)
    missing = questions.list_missing_fields(lead)
    # Pending confirmations also count toward "known" progress.
    pending_confirm = list(lead.fields_to_confirm)
    total = len(complete) + len(missing) + len(pending_confirm)
    if total == 0:
        return 100
    done = len(complete)
    return max(0, min(100, int(round((done / total) * 100))))
