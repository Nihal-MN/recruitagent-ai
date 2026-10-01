"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.routes import health
from app.core.config import get_settings
from app.core.errors import AppError


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Human-in-the-loop AI recruiting operations agent. The model never "
            "writes directly to the database; every consequential write goes "
            "through a persisted approval. No autonomous hire/reject decisions."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Total-Count"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code if hasattr(exc, "status_code") else 409,
            content={
                "error": {"code": exc.code.value, "message": exc.message, "detail": exc.detail}
            },
        )

    app.include_router(health.router, prefix="/api/v1", tags=["system"])

    return app


app = create_app()
