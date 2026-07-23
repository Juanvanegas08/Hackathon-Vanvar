"""Shared API schemas."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Health-check payload."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"status": "ok", "service": "CasaLista Voice API"}]
        }
    )

    status: str = Field(examples=["ok"])
    service: str = Field(examples=["CasaLista Voice API"])


class DatabaseHealthResponse(BaseModel):
    """Database-specific health payload (never includes secrets)."""

    status: str
    database: dict[str, Any]


class ErrorResponse(BaseModel):
    """Standard error body."""

    detail: str
    code: str | None = None


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
