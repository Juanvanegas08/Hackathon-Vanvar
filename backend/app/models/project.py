"""Project catalog models for future recommendation support."""

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class HistoricalProfile(BaseModel):
    """Aggregated historical buyer profile for a project."""

    affiliated_percentage: float | None = None
    salary_range_distribution: dict[str, float] = Field(default_factory=dict)
    segments: dict[str, float] = Field(default_factory=dict)
    dependents_distribution: dict[str, float] = Field(default_factory=dict)
    frequent_locations: list[str] = Field(default_factory=list)
    frequent_financial_entities: list[str] = Field(default_factory=list)
    frequent_companies: list[str] = Field(default_factory=list)


class Project(BaseModel):
    """Housing project entity prepared for a future recommender."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "00000000-0000-0000-0000-000000000010",
                    "nombre": "Proyecto Ejemplo",
                    "codigo": "PRY-001",
                    "etapa": "En ventas",
                    "ubicacion": "Bogotá",
                    "municipio": "Bogotá",
                    "departamento": "Cundinamarca",
                    "valor_minimo": 120000000,
                    "valor_maximo": 280000000,
                    "brochure_url": None,
                    "recorrido_360_url": None,
                    "disponible": True,
                    "perfil_historico": {
                        "affiliated_percentage": 92.5,
                        "salary_range_distribution": {},
                        "segments": {},
                        "dependents_distribution": {},
                        "frequent_locations": [],
                        "frequent_financial_entities": [],
                        "frequent_companies": [],
                    },
                    "metadata": {},
                }
            ]
        }
    )

    id: UUID = Field(default_factory=uuid4)
    nombre: str
    codigo: str | None = None
    etapa: str | None = None
    ubicacion: str | None = None
    municipio: str | None = None
    departamento: str | None = None
    valor_minimo: float | None = None
    valor_maximo: float | None = None
    brochure_url: str | None = None
    recorrido_360_url: str | None = None
    disponible: bool = True
    perfil_historico: HistoricalProfile = Field(default_factory=HistoricalProfile)
    metadata: dict[str, Any] = Field(default_factory=dict)
