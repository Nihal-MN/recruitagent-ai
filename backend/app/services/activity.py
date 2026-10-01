"""Append-only activity log — proposals, approvals, executions, moves."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import ActivityEvent


def log(
    db: Session,
    event_type: str,
    summary: str,
    *,
    conversation_id: int | None = None,
    approval_id: int | None = None,
    candidate_id: int | None = None,
    job_id: int | None = None,
    application_id: int | None = None,
    payload: dict | None = None,
) -> ActivityEvent:
    event = ActivityEvent(
        type=event_type,
        summary=summary,
        conversation_id=conversation_id,
        approval_id=approval_id,
        candidate_id=candidate_id,
        job_id=job_id,
        application_id=application_id,
        payload=payload,
    )
    db.add(event)
    db.flush()
    return event
