"""System health — live database + AI mode, never a secret."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select

from app import __version__
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import (
    AgentConversation,
    Application,
    ApprovalRequest,
    ApprovalStatus,
    Candidate,
    Job,
)

router = APIRouter()


@router.get("/health/live", summary="Liveness probe")
def health_live() -> dict:
    return {"status": "ok"}


@router.get("/health", summary="Full system health")
def health() -> dict:
    settings = get_settings()
    db_status: dict = {"status": "ok", "dialect": None, "detail": None}
    counts: dict = {}
    try:
        with SessionLocal() as db:
            counts = {
                "candidates": db.scalar(select(func.count(Candidate.id))) or 0,
                "jobs": db.scalar(select(func.count(Job.id))) or 0,
                "applications": db.scalar(select(func.count(Application.id))) or 0,
                "conversations": db.scalar(select(func.count(AgentConversation.id))) or 0,
                "pending_approvals": db.scalar(
                    select(func.count(ApprovalRequest.id)).where(
                        ApprovalRequest.status == ApprovalStatus.PENDING
                    )
                )
                or 0,
            }
            db_status["dialect"] = db.get_bind().dialect.name
    except Exception as exc:  # pragma: no cover - surfaced to the operator
        db_status = {"status": "error", "dialect": None, "detail": str(exc)}

    provider = settings.resolved_provider
    return {
        "status": "ok" if db_status["status"] == "ok" else "degraded",
        "app": settings.app_name,
        "version": __version__,
        "database": db_status,
        "ai": {
            "mode": settings.ai_provider,  # auto | openai | mock
            "provider": "openai" if provider == "openai" else "demo",
            "provider_label": (
                "OpenAI tool calling" if provider == "openai" else "deterministic demo agent"
            ),
            "model": settings.resolved_model if provider == "openai" else "deterministic-rules-v1",
            "api_key_configured": bool(settings.openai_api_key.strip()),
        },
        "counts": counts,
    }
