"""Standalone evaluation endpoints."""

from decimal import Decimal

from fastapi import APIRouter, Depends

from app.api.deps import get_affiliation_service
from app.schemas.evaluation import AffiliationCategoryRequest, AffiliationCategoryResponse
from app.services.affiliation_service import AffiliationService

router = APIRouter(prefix="/evaluation", tags=["Evaluación"])


@router.post(
    "/affiliation-category",
    response_model=AffiliationCategoryResponse,
    summary="Calcular categoría de afiliación",
    description=(
        "Calcula la categoría A/B/C/D a partir de afiliación y salario personal. "
        "Requiere SMMLV configurado cuando el lead es afiliado."
    ),
    responses={
        400: {"description": "SMMLV no configurado u otro error de negocio"},
        422: {"description": "Payload inválido"},
    },
)
def calculate_affiliation_category(
    payload: AffiliationCategoryRequest,
    service: AffiliationService = Depends(get_affiliation_service),
) -> AffiliationCategoryResponse:
    result = service.calculate_category(
        afiliado=payload.afiliado,
        salario_mensual=payload.salario_mensual,
        afiliacion_confirmada=payload.afiliacion_confirmada,
    )
    salario_smmlv: float | None
    if isinstance(result.salario_en_smmlv, Decimal):
        salario_smmlv = float(result.salario_en_smmlv)
    else:
        salario_smmlv = None

    return AffiliationCategoryResponse(
        categoria=result.categoria,
        salario_en_smmlv=salario_smmlv,
        requiere_confirmacion=result.requiere_confirmacion,
        afiliado=result.afiliado,
        salario_mensual=result.salario_mensual,
        fuente=result.fuente.value,
    )
