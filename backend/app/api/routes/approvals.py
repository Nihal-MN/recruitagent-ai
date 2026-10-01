"""Approvals — the human decision surface. Backend-enforced execution."""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import DbSession
from app.api.schemas import ApprovalDecision, ApprovalOut
from app.models import ApprovalRequest
from app.services import approvals as approvals_service

router = APIRouter()


@router.get("/approvals", response_model=list[ApprovalOut], summary="List approval requests")
def list_approvals(
    db: DbSession,
    status: str | None = Query(None, description="Filter by status (PENDING, EXECUTED, …)"),
    limit: int = Query(50, ge=1, le=200),
) -> list[ApprovalOut]:
    stmt = select(ApprovalRequest).order_by(ApprovalRequest.id.desc()).limit(limit)
    if status:
        stmt = stmt.where(ApprovalRequest.status == status.upper())
    rows = db.scalars(stmt)
    return [ApprovalOut.model_validate(a, from_attributes=True) for a in rows]


@router.post(
    "/approvals/{approval_id}/approve",
    response_model=ApprovalOut,
    summary="Approve — executes the exact validated action, exactly once",
)
def approve(approval_id: int, payload: ApprovalDecision, db: DbSession) -> ApprovalOut:
    request = approvals_service.approve(db, approval_id, decided_by=payload.decided_by)
    db.commit()
    db.refresh(request)
    return ApprovalOut.model_validate(request, from_attributes=True)


@router.post(
    "/approvals/{approval_id}/reject",
    response_model=ApprovalOut,
    summary="Reject — zero mutation, guaranteed",
)
def reject(approval_id: int, payload: ApprovalDecision, db: DbSession) -> ApprovalOut:
    request = approvals_service.reject(db, approval_id, decided_by=payload.decided_by)
    db.commit()
    db.refresh(request)
    return ApprovalOut.model_validate(request, from_attributes=True)
