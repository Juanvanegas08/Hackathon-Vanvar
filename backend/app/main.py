"""FastAPI application entrypoint for CasaLista Voice."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.api.router import build_api_router
from app.api.routes import health
from app.core.config import get_settings
from app.core.exceptions import (
    AppError,
    NotFoundError,
    RealtimeServiceError,
    ValidationBusinessError,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Application lifespan hook."""
    yield


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        description=(
            "Backend inicial de perfilamiento para CasaLista Voice. "
            "Permite crear leads, determinar la siguiente pregunta, calcular "
            "categoría de afiliación y generar una evaluación preliminar "
            "orientativa (no es aprobación crediticia)."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health.router)
    application.include_router(build_api_router())
    register_exception_handlers(application)
    return application


def register_exception_handlers(application: FastAPI) -> None:
    """Register centralized exception handlers."""

    @application.exception_handler(RealtimeServiceError)
    async def realtime_error_handler(
        _: Request,
        exc: RealtimeServiceError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": exc.message, "code": exc.code},
        )

    @application.exception_handler(NotFoundError)
    async def not_found_handler(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"detail": exc.message, "code": exc.code},
        )

    @application.exception_handler(ValidationBusinessError)
    async def business_validation_handler(
        _: Request,
        exc: ValidationBusinessError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"detail": exc.message, "code": exc.code},
        )

    @application.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        status_code = 400 if exc.code == "configuration_error" else 500
        return JSONResponse(
            status_code=status_code,
            content={"detail": exc.message, "code": exc.code},
        )

    @application.exception_handler(RequestValidationError)
    async def request_validation_handler(
        _: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "code": "request_validation_error"},
        )

    @application.exception_handler(ValidationError)
    async def pydantic_validation_handler(
        _: Request,
        exc: ValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "code": "validation_error"},
        )

app = create_app()
