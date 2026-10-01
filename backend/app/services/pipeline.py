"""Pipeline: board view, find-or-create applications, guarded stage moves."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.models import ALL_STAGES, Application, Candidate, Job
from app.services import activity


def get_board(db: Session, job_id: int | None = None) -> dict:
    stmt = select(Application).order_by(Application.updated_at.desc())
    if job_id is not None:
        stmt = stmt.where(Application.job_id == job_id)
    rows = list(db.scalars(stmt))

    columns: dict[str, list[dict]] = {
        stage: []
        for stage in ("NEW", "SCREENING", "SHORTLISTED", "INTERVIEW", "OFFER", "HIRED", "REJECTED")
    }
    for application in rows:
        columns[application.stage].append(
            {
                "application_id": application.id,
                "candidate_id": application.candidate_id,
                "candidate_name": application.candidate.full_name,
                "job_id": application.job_id,
                "job_title": application.job.title,
                "stage": application.stage,
                "updated_at": application.updated_at.isoformat(),
            }
        )
    return {"columns": columns, "total": len(rows)}


def find_application(db: Session, candidate_id: int, job_id: int) -> Application | None:
    return db.scalar(
        select(Application).where(
            Application.candidate_id == candidate_id, Application.job_id == job_id
        )
    )


def ensure_application(db: Session, candidate: Candidate, job: Job) -> Application:
    application = find_application(db, candidate.id, job.id)
    if application is None:
        application = Application(candidate_id=candidate.id, job_id=job.id, stage="NEW")
        db.add(application)
        db.flush()
        activity.log(
            db,
            "stage_moved",
            f"Added {candidate.full_name} to '{job.title}' at NEW.",
            candidate_id=candidate.id,
            job_id=job.id,
            application_id=application.id,
            payload={"to_stage": "NEW"},
        )
    return application


def move_application_stage(
    db: Session,
    application: Application,
    to_stage: str,
    *,
    note: str | None = None,
    actor: str = "recruiter",
    approval_id: int | None = None,
) -> dict:
    """Guarded stage move. Called only after policy/approval (see approvals service)."""
    to_stage = (to_stage or "").upper().strip()
    if to_stage not in ALL_STAGES:
        raise AppError(
            ErrorCode.validation_error,
            f"Unknown stage '{to_stage}'. Valid stages: {', '.join(ALL_STAGES)}.",
        )
    if application.stage == to_stage:
        raise AppError(
            ErrorCode.policy_blocked,
            f"{application.candidate.full_name} is already at {to_stage} — nothing to do.",
        )

    previous = application.stage
    application.stage = to_stage
    db.flush()
    activity.log(
        db,
        "stage_moved",
        f"{application.candidate.full_name} — '{application.job.title}': {previous} → {to_stage}"
        + (f" ({note})" if note else ""),
        approval_id=approval_id,
        candidate_id=application.candidate_id,
        job_id=application.job_id,
        application_id=application.id,
        payload={"from_stage": previous, "to_stage": to_stage, "actor": actor, "note": note},
    )
    return {
        "application_id": application.id,
        "candidate_name": application.candidate.full_name,
        "job_title": application.job.title,
        "from_stage": previous,
        "to_stage": to_stage,
    }
