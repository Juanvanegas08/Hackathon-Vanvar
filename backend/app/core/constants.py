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

# Recommendation weights (must sum conceptually to 100 when all criteria apply).
RECOMMENDATION_WEIGHTS: Final[dict[str, int]] = {
    "ubicacion": 25,
    "compatibilidad_economica": 20,
    "afiliacion": 15,
    "segmento": 15,
    "composicion_familiar": 10,
    "proyecto_interes": 10,
    "preferencias_adicionales": 5,
}

RECOMMENDATION_ESSENTIAL_FIELDS: Final[tuple[str, ...]] = (
    "afiliado",
    "salario_mensual",
    "ubicacion_deseada",
)

RECOMMENDATION_DISCLAIMER: Final[str] = (
    "Las recomendaciones son orientativas y no constituyen aprobación de crédito "
    "ni garantía de disponibilidad."
)

ECONOMIC_COMPATIBILITY_DISCLAIMER: Final[str] = (
    "La compatibilidad económica es orientativa y no constituye una aprobación "
    "de crédito ni una validación financiera oficial."
)

# Confidence thresholds for recommendations.
RECOMMENDATION_CONFIDENCE: Final[dict[str, int | float]] = {
    "min_historical_sample_for_high": 30,
    "min_historical_sample_for_medium": 10,
    "min_criteria_for_high": 4,
    "min_criteria_for_medium": 2,
    "min_lead_fields_for_high": 5,
}

# Prices above this median (COP) are treated as unreliable for filtering/scoring.
HISTORICAL_PRICE_RELIABILITY_MAX_MEDIAN: Final[float] = 1_000_000_000

PROJECT_NAME_STOPWORDS: Final[frozenset[str]] = frozenset(
    {
        "agrupacion",
        "de",
        "vivienda",
        "conjunto",
        "residencial",
        "proyecto",
        "ciudadela",
        "colsubsidio",
        "el",
        "la",
        "los",
        "las",
        "del",
    }
)
