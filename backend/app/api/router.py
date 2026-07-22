"""API router aggregation."""

from fastapi import APIRouter

from app.api.routes import evaluation, health, leads
from app.core.config import get_settings


def build_api_router() -> APIRouter:
    """Compose versioned API routes."""
    settings = get_settings()
    api_router = APIRouter(prefix=settings.api_prefix)
    api_router.include_router(leads.router)
    api_router.include_router(evaluation.router)
    # Health is also mounted at root in main.py; keep a versioned alias.
    api_router.include_router(health.router)
    return api_router
