"""Affiliation category calculation (A/B/C/D)."""

from decimal import ROUND_HALF_UP, Decimal

from app.core.config import Settings, get_settings
from app.core.exceptions import InvalidSmmlvError, ValidationBusinessError
from app.models.evaluation import AffiliationCategoryResult, CategorySource
from app.models.lead import AffiliationCategory


class AffiliationService:
    """Compute Colsubsidio affiliation salary categories from personal salary."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def calculate_category(
        self,
        *,
        afiliado: bool | None,
        salario_mensual: float | None,
        afiliacion_confirmada: bool = False,
    ) -> AffiliationCategoryResult:
        """Calculate affiliation category using personal employer-reported salary.

        Rules:
        - A: affiliated, salary <= 2 SMMLV
        - B: affiliated, salary > 2 and <= 4 SMMLV
        - C: affiliated, salary > 4 SMMLV
        - D: not affiliated (salary not required)
        - Unknown affiliation or affiliated without salary => undetermined
        """
        if salario_mensual is not None and salario_mensual < 0:
            raise ValidationBusinessError(
                "El salario mensual no puede ser negativo",
                code="negative_salary",
            )

        requiere_confirmacion = not afiliacion_confirmada

        if afiliado is None:
            return AffiliationCategoryResult(
                afiliado=None,
                categoria=None,
                salario_mensual=salario_mensual,
                salario_en_smmlv=None,
                fuente=CategorySource.INDETERMINADA,
                requiere_confirmacion=True,
            )

        if afiliado is False:
            return AffiliationCategoryResult(
                afiliado=False,
                categoria=AffiliationCategory.D,
                salario_mensual=salario_mensual,
                salario_en_smmlv=self._salary_in_smmlv(salario_mensual)
                if salario_mensual is not None
                else None,
                fuente=CategorySource.CALCULADA,
                requiere_confirmacion=requiere_confirmacion,
            )

        # Affiliated path requires a configured SMMLV and a known personal salary.
        if not self._settings.is_smmlv_configured:
            raise InvalidSmmlvError()

        if salario_mensual is None:
            return AffiliationCategoryResult(
                afiliado=True,
                categoria=None,
                salario_mensual=None,
                salario_en_smmlv=None,
                fuente=CategorySource.INDETERMINADA,
                requiere_confirmacion=requiere_confirmacion,
            )

        ratio = self._salary_ratio(salario_mensual)
        assert ratio is not None
        salario_en_smmlv = ratio.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Compare the exact ratio so values just above 4 SMMLV are not rounded into B.
        if ratio <= Decimal("2"):
            categoria = AffiliationCategory.A
        elif ratio <= Decimal("4"):
            categoria = AffiliationCategory.B
        else:
            categoria = AffiliationCategory.C

        return AffiliationCategoryResult(
            afiliado=True,
            categoria=categoria,
            salario_mensual=salario_mensual,
            salario_en_smmlv=salario_en_smmlv,
            fuente=CategorySource.CALCULADA,
            requiere_confirmacion=requiere_confirmacion,
        )

    def _salary_in_smmlv(self, salario_mensual: float) -> Decimal | None:
        ratio = self._salary_ratio(salario_mensual)
        if ratio is None:
            return None
        return ratio.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _salary_ratio(self, salario_mensual: float) -> Decimal | None:
        if not self._settings.is_smmlv_configured:
            return None
        smmlv = Decimal(str(self._settings.smmlv))
        salary = Decimal(str(salario_mensual))
        return salary / smmlv
