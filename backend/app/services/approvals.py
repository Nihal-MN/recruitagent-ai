"""Approvals — the backend-enforced gate for every consequential write.

Guarantees (tested in tests/test_approvals.py and evals):

- a PENDING approval mutates nothing;
- REJECTED → zero mutation, ever;
- APPROVED executes the exact validated arguments **exactly once**, even under
  retries/replays (status machine + unique idempotency key);
- every transition lands in the activity log.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.models import ApprovalRequest, ApprovalStatus
from app.services import activity

#: Policy: ALL agent-initiated writes require approval (documented in
#: docs/AGENT_DESIGN.md — notes included, so the policy is consistent).
APPROVAL_REQUIRED_TOOLS = ("update_pipeline", "add_candidate_note")


def idempotency_key(conversation_id: int | None, tool_name: str, args: dict) -> str:
    payload = json.dumps(
        {"conversation_id": conversation_id, "tool_name": tool_name, "args": args},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:48]


def create_or_get_request(
    db: Session,
    *,
    conversation_id: int | None,
    tool_name: str,
    args: dict,
    summary: str,
) -> tuple[ApprovalRequest, bool]:
    """Create a PENDING approval; never duplicate a live or executed one.

    Replay protection, precisely scoped:

    - an identical PENDING request is reused (no duplicate approvals in the UI);
    - an identical EXECUTED request is returned as-is (the orchestrator reports
      "already executed" — a second execution can never happen);
    - after REJECTED/FAILED the recruiter may change their mind: a *new*
      attempt is created (same action, new request), because a rejection is a
      decision on that request — not a permanent block on the action.
    """
    base_key = idempotency_key(conversation_id, tool_name, args)
    attempts = list(
        db.scalars(
            select(ApprovalRequest)
            .where(
                (ApprovalRequest.idempotency_key == base_key)
                | (ApprovalRequest.idempotency_key.like(f"{base_key}-r%"))
            )
            .order_by(ApprovalRequest.id.desc())
        )
    )
    latest = attempts[0] if attempts else None
    if latest is not None and latest.status in (
        ApprovalStatus.PENDING,
        ApprovalStatus.EXECUTING,
        ApprovalStatus.EXECUTED,
    ):
        return latest, False

    key = base_key if latest is None else f"{base_key}-r{len(attempts) + 1}"
    request = ApprovalRequest(
        conversation_id=conversation_id,
        tool_name=tool_name,
        args_json=args,
        summary=summary,
        status=ApprovalStatus.PENDING,
        idempotency_key=key,
    )
    db.add(request)
    db.flush()
    activity.log(
        db,
        "approval_requested",
        f"Approval requested: {summary}",
        conversation_id=conversation_id,
        approval_id=request.id,
        candidate_id=args.get("candidate_id"),
        job_id=args.get("job_id"),
    )
    return request, True


def get_request(db: Session, request_id: int) -> ApprovalRequest:
    request = db.get(ApprovalRequest, request_id)
    if request is None:
        raise AppError(ErrorCode.entity_not_found, f"No approval request with id {request_id}.")
    return request


def approve(db: Session, request_id: int, *, decided_by: str = "recruiter") -> ApprovalRequest:
    request = get_request(db, request_id)

    # Exactly-once: a replayed approval of an already-executed request is a
    # no-op that returns the original outcome. No second execution. Ever.
    if request.status == ApprovalStatus.EXECUTED:
        return request
    if request.status == ApprovalStatus.EXECUTING:
        raise AppError(ErrorCode.policy_blocked, "This approval is already executing.")
    if request.status == ApprovalStatus.REJECTED:
        raise AppError(
            ErrorCode.approval_rejected,
            "This request was rejected. Nothing will be executed; propose a new request instead.",
        )
    if request.status == ApprovalStatus.FAILED:
        raise AppError(
            ErrorCode.policy_blocked,
            "This approval previously failed during execution. Propose a new request instead.",
        )

    request.status = ApprovalStatus.APPROVED
    request.decided_at = datetime.now(UTC)
    request.decided_by = decided_by
    request.status = ApprovalStatus.EXECUTING
    db.flush()
    activity.log(
        db,
        "approval_approved",
        f"Approved by {decided_by}: {request.summary}",
        conversation_id=request.conversation_id,
        approval_id=request.id,
    )

    # Execute the exact validated arguments once.
    from app.tools.executor import execute_tool  # local import: avoids a cycle
    from app.tools.registry import ToolContext, get_tool

    spec = get_tool(request.tool_name)
    if spec is None:
        request.status = ApprovalStatus.FAILED
        request.error_code = ErrorCode.tool_failed.value
        db.flush()
        raise AppError(
            ErrorCode.tool_failed, f"Tool '{request.tool_name}' no longer exists; nothing executed."
        )

    outcome = execute_tool(
        db,
        request.tool_name,
        dict(request.args_json or {}),
        ToolContext(
            conversation_id=request.conversation_id, actor=decided_by, approval_id=request.id
        ),
    )

    if outcome.ok and outcome.result is not None:
        request.status = ApprovalStatus.EXECUTED
        request.executed_at = datetime.now(UTC)
        request.result_summary = spec.summarizes_as(outcome.result)
        db.flush()
        activity.log(
            db,
            "tool_executed",
            f"Executed after approval: {request.summary}",
            conversation_id=request.conversation_id,
            approval_id=request.id,
            candidate_id=(request.args_json or {}).get("candidate_id"),
            job_id=(request.args_json or {}).get("job_id"),
            payload={"result": request.result_summary},
        )
        return request

    request.status = ApprovalStatus.FAILED
    request.error_code = outcome.error_code
    request.result_summary = outcome.error_message
    db.flush()
    raise AppError(
        ErrorCode.tool_failed,
        f"The approved action failed and nothing was changed: {outcome.error_message}",
    )


def reject(db: Session, request_id: int, *, decided_by: str = "recruiter") -> ApprovalRequest:
    request = get_request(db, request_id)
    if request.status != ApprovalStatus.PENDING:
        raise AppError(
            ErrorCode.policy_blocked,
            f"Only PENDING requests can be rejected (current status: {request.status}).",
        )
    request.status = ApprovalStatus.REJECTED
    request.decided_at = datetime.now(UTC)
    request.decided_by = decided_by
    db.flush()
    activity.log(
        db,
        "approval_rejected",
        f"Rejected by {decided_by}: {request.summary} (nothing changed)",
        conversation_id=request.conversation_id,
        approval_id=request.id,
    )
    return request
