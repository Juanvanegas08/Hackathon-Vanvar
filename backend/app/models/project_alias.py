"""Canonical project identity models."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.project import HistoricalProfile


class ProjectAliasGroup(BaseModel):
    """Manual alias group for a canonical project."""

    canonical_name: str
    aliases: list[str] = Field(default_factory=list)


class CanonicalProject(BaseModel):
    """Consolidated project used by the recommender."""

    canonical_project_id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    catalog_records: list[dict[str, Any]] = Field(default_factory=list)
    historical_profile: HistoricalProfile = Field(default_factory=HistoricalProfile)
    brochure_url: str | None = None
    tour_360_url: str | None = None
    available: bool = True
    codigo: str | None = None
    etapa: str | None = None
    ubicacion: str | None = None
    municipio: str | None = None
    departamento: str | None = None
    valor_minimo: float | None = None
    valor_maximo: float | None = None
    primary_catalog_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
