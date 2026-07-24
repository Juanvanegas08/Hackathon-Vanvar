"""API router aggregation."""

from fastapi import APIRouter

from app.api.routes import (
    evaluation,
    health,
    identity,
    leads,
    phone_calls,
    projects,
    realtime,
    recommendations,
    twilio_voice,
    voice,
)
from app.core.config import get_settings


def build_api_router() -> APIRouter:
    """Compose versioned API routes."""
    settings = get_settings()
    api_router = APIRouter(prefix=settings.api_prefix)
    # Identity routes include /leads/from-identity and must precede /leads/{id}.
    api_router.include_router(identity.router)
    api_router.include_router(leads.router)
    api_router.include_router(recommendations.router)
    api_router.include_router(projects.router)
    api_router.include_router(evaluation.router)
    api_router.include_router(realtime.router)
    api_router.include_router(voice.router)
    api_router.include_router(phone_calls.router)
    api_router.include_router(twilio_voice.router)
    # Health is also mounted at root in main.py; keep a versioned alias.
    api_router.include_router(health.router)
    return api_router
