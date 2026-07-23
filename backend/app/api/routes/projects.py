"""Read-only project catalog endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_project_profile_service
from app.core.exceptions import NotFoundError
from app.schemas.recommendation import ProjectResponse
from app.services.project_profile_service import ProjectProfileService

router = APIRouter(prefix="/projects", tags=["Proyectos"])


@router.get(
    "",
    response_model=list[ProjectResponse],
    summary="Listar proyectos",
    description="Lista el catálogo de proyectos desde los archivos procesados.",
)
def list_projects(
    disponible: bool | None = Query(default=None),
    municipio: str | None = Query(default=None),
    departamento: str | None = Query(default=None),
    nombre: str | None = Query(default=None, description="Búsqueda parcial por nombre"),
    service: ProjectProfileService = Depends(get_project_profile_service),
) -> list[ProjectResponse]:
    projects = service.list_projects(
        disponible=disponible,
        municipio=municipio,
        departamento=departamento,
        nombre=nombre,
    )
    return [ProjectResponse.model_validate(project) for project in projects]


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Obtener proyecto",
    description="Consulta un proyecto del catálogo por UUID.",
    responses={404: {"description": "Proyecto no encontrado"}},
)
def get_project(
    project_id: UUID,
    service: ProjectProfileService = Depends(get_project_profile_service),
) -> ProjectResponse:
    project = service.get_project(project_id)
    if project is None:
        raise NotFoundError(f"Proyecto {project_id} no encontrado")
    return ProjectResponse.model_validate(project)
