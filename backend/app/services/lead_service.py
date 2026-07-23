"""Lead orchestration service."""

from uuid import UUID

from app.core.exceptions import InvalidSmmlvError, NotFoundError
from app.models.lead import AffiliationCategory, Lead
from app.repositories.lead_repository import LeadRepository
from app.schemas.evaluation import (
    AdvisorSummaryResponse,
    NextQuestionResponse,
    ReadinessResponse,
)
from app.schemas.lead import LeadCreate, LeadUpdate
from app.services.affiliation_service import AffiliationService
from app.services.question_service import QuestionService
from app.services.readiness_service import ReadinessService
from app.services.summary_service import SummaryService


class LeadService:
    """Coordinate lead CRUD and profiling workflows."""

    def __init__(
        self,
        repository: LeadRepository,
        affiliation_service: AffiliationService | None = None,
        question_service: QuestionService | None = None,
        readiness_service: ReadinessService | None = None,
        summary_service: SummaryService | None = None,
    ) -> None:
        self._repository = repository
        self._affiliation = affiliation_service or AffiliationService()
        self._questions = question_service or QuestionService()
        self._readiness = readiness_service or ReadinessService(self._questions)
        self._summary = summary_service or SummaryService(
            readiness_service=self._readiness,
            affiliation_service=self._affiliation,
        )

    def create_lead(self, payload: LeadCreate) -> Lead:
        lead = Lead.model_validate(payload.model_dump())
        lead = self._enrich_category(lead)
        return self._repository.create(lead)

    def list_leads(self) -> list[Lead]:
        return self._repository.list_all()

    def get_lead(self, lead_id: UUID) -> Lead:
        lead = self._repository.get_by_id(lead_id)
        if lead is None:
            raise NotFoundError(f"Lead {lead_id} no encontrado")
        return lead

    def update_lead(self, lead_id: UUID, payload: LeadUpdate) -> Lead:
        lead = self.get_lead(lead_id)
        updates = payload.model_dump(exclude_unset=True)
        updated = lead.apply_partial_update(updates)
        updated = self._enrich_category(updated)
        return self._repository.update(updated)

    def apply_lead_updates(self, lead_id: UUID, updates: dict[str, object]) -> Lead:
        """Apply a raw partial update dict (including field_metadata)."""
        lead = self.get_lead(lead_id)
        updated = lead.apply_partial_update(updates)
        updated = self._enrich_category(updated)
        return self._repository.update(updated)

    def delete_lead(self, lead_id: UUID) -> None:
        deleted = self._repository.delete(lead_id)
        if not deleted:
            raise NotFoundError(f"Lead {lead_id} no encontrado")

    def next_question(self, lead_id: UUID) -> NextQuestionResponse:
        lead = self.get_lead(lead_id)
        return self._questions.get_next_question(lead)

    def evaluate(self, lead_id: UUID) -> ReadinessResponse:
        lead = self.get_lead(lead_id)
        result = self._readiness.evaluate(lead)
        updated = lead.apply_partial_update(
            {
                "estado_lead": result.status,
                "categoria_afiliacion": self._safe_category(lead),
            }
        )
        self._repository.update(updated)
        return ReadinessResponse.model_validate(result.model_dump())

    def summary(self, lead_id: UUID) -> AdvisorSummaryResponse:
        lead = self.get_lead(lead_id)
        readiness = self._readiness.evaluate(lead)
        return self._summary.build_summary(lead, readiness)

    def _enrich_category(self, lead: Lead) -> Lead:
        category = self._safe_category(lead)
        if category is None and lead.categoria_afiliacion is None:
            return lead
        if category == lead.categoria_afiliacion:
            return lead
        return lead.apply_partial_update({"categoria_afiliacion": category})

    def _safe_category(self, lead: Lead) -> AffiliationCategory | None:
        try:
            result = self._affiliation.calculate_category(
                afiliado=lead.afiliado,
                salario_mensual=lead.salario_mensual,
                afiliacion_confirmada=lead.afiliacion_confirmada,
            )
            return result.categoria
        except InvalidSmmlvError:
            # Keep lead usable even when SMMLV is not yet configured.
            if lead.afiliado is False:
                return AffiliationCategory.D
            return lead.categoria_afiliacion
