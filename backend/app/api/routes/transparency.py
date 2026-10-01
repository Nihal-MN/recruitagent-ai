"""Activity log, tool trace and pipeline board — the transparency surfaces."""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import DbSession
from app.api.schemas import ActivityOut, ToolExecutionOut
from app.models import ActivityEvent, ToolExecution
from app.services import pipeline as pipeline_service

router = APIRouter()


@router.get("/activity", response_model=list[ActivityOut], summary="Audit trail (newest first)")
def list_activity(
    db: DbSession, limit: int = Query(100, ge=1, le=500)
) -> list[ActivityOut]:
    rows = db.scalars(select(ActivityEvent).order_by(ActivityEvent.id.desc()).limit(limit))
    return [ActivityOut.model_validate(e, from_attributes=True) for e in rows]


@router.get(
    "/tool-executions",
    response_model=list[ToolExecutionOut],
    summary="Safe operational tool trace (never hidden model reasoning)",
)
def list_tool_executions(
    db: DbSession,
    conversation_id: int | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> list[ToolExecutionOut]:
    stmt = select(ToolExecution).order_by(ToolExecution.id.desc()).limit(limit)
    if conversation_id is not None:
        stmt = stmt.where(ToolExecution.conversation_id == conversation_id)
        stmt = stmt.order_by(ToolExecution.step_number.asc(), ToolExecution.id.asc())
    rows = db.scalars(stmt)
    return [ToolExecutionOut.model_validate(e, from_attributes=True) for e in rows]


@router.get("/pipeline", summary="Pipeline board, optionally per job")
def pipeline_board(db: DbSession, job_id: int | None = Query(None)) -> dict:
    return pipeline_service.get_board(db, job_id=job_id)
