"""Shared constants and future business-rule interfaces."""

from dataclasses import dataclass
from typing import Final


# Future 90/10 sales mix constraint (not enforced yet).
@dataclass(frozen=True, slots=True)
class AffiliationSalesQuotaConfig:
    """Configurable sales-mix restriction for affiliated vs non-affiliated buyers.

    This is intentionally not wired to a live sales counter in this phase.
    """

    min_affiliated_percentage: float = 90.0
    max_non_affiliated_percentage: float = 10.0
    measurement_period: str = "monthly"
    non_affiliated_slots_available: bool | None = None


DEFAULT_AFFILIATION_SALES_QUOTA: Final[AffiliationSalesQuotaConfig] = (
    AffiliationSalesQuotaConfig()
)


# Readiness score weights (profile completeness / readiness, not credit approval).
READINESS_WEIGHTS: Final[dict[str, int]] = {
    "affiliation_identified": 15,
    "personal_income_known": 10,
    "household_income_known": 10,
    "savings_known": 15,
    "obligations_known": 10,
    "housing_status_known": 10,
    "credit_situation_known": 10,
    "desired_location_known": 5,
    "purchase_timeline_known": 10,
    "household_composition_known": 5,
}

CRITICAL_READINESS_FIELDS: Final[tuple[str, ...]] = (
    "afiliado",
    "salario_mensual",
    "ahorro",
)

READINESS_DISCLAIMER: Final[str] = (
    "Resultado orientativo. No constituye una aprobación de crédito hipotecario."
)
