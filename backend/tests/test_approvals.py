"""Approval lifecycle — reject no-mutation, approve exactly-once, attempts."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.models import (
    ActivityEvent,
    Application,
    ApprovalStatus,
    Candidate,
    Job,
)
from app.services import approvals


def _pair(db) -> tuple[Candidate, Job, Application]:
    candidate = db.scalar(select(Candidate).where(Candidate.full_name == "Amira Haddad"))
    job = db.scalar(select(Job).where(Job.title == "Senior Backend Engineer"))
    application = db.scalar(
        select(Application).where(
            Application.candidate_id == candidate.id, Application.job_id == job.id
        )
    )
    assert application is not None
    return candidate, job, application


def _propose_move(db, candidate, job, stage="INTERVIEW"):
    request, created = approvals.create_or_get_request(
        db,
        conversation_id=None,
        tool_name="update_pipeline",
        args={"candidate_id": candidate.id, "job_id": job.id, "to_stage": stage},
        summary=f"Move {candidate.full_name} to {stage}.",
    )
    assert created
    return request


def _stage_moved_events(db) -> int:
    return (
        db.scalar(
            select(func.count(ActivityEvent.id)).where(ActivityEvent.type == "stage_moved")
        )
        or 0
    )


def test_pending_request_does_not_mutate(db):
    candidate, job, application = _pair(db)
    before = application.stage
    _propose_move(db, candidate, job)
    db.commit()
    db.refresh(application)
    assert application.stage == before


def test_reject_causes_zero_mutation(db):
    candidate, job, application = _pair(db)
    before = application.stage
    request = _propose_move(db, candidate, job)
    db.commit()

    approvals.reject(db, request.id, decided_by="tester")
    db.commit()

    db.refresh(application)
    db.refresh(request)
    assert request.status == ApprovalStatus.REJECTED
    assert application.stage == before
    assert _stage_moved_events(db) == 0


def test_approve_executes_exactly_once_even_on_replay(db):
    candidate, job, application = _pair(db)
    request = _propose_move(db, candidate, job)
    db.commit()

    approvals.approve(db, request.id, decided_by="tester")
    db.commit()
    db.refresh(application)
    db.refresh(request)
    assert request.status == ApprovalStatus.EXECUTED
    assert application.stage == "INTERVIEW"
    assert _stage_moved_events(db) == 1

    # Replay: same request id again — must return the original outcome, no re-run.
    approvals.approve(db, request.id, decided_by="tester")
    db.commit()
    assert _stage_moved_events(db) == 1
    assert request.status == ApprovalStatus.EXECUTED


def test_approving_a_rejected_request_is_refused(db):
    candidate, job, _ = _pair(db)
    request = _propose_move(db, candidate, job)
    db.commit()
    approvals.reject(db, request.id)
    db.commit()
    with pytest.raises(AppError) as err:
        approvals.approve(db, request.id)
    assert err.value.code.value == "approval_rejected"


def test_new_attempt_after_rejection(db):
    candidate, job, _ = _pair(db)
    first = _propose_move(db, candidate, job)
    db.commit()
    approvals.reject(db, first.id)
    db.commit()

    second, created = approvals.create_or_get_request(
        db,
        conversation_id=None,
        tool_name="update_pipeline",
        args={"candidate_id": candidate.id, "job_id": job.id, "to_stage": "INTERVIEW"},
        summary="Move again.",
    )
    assert created and second.id != first.id and second.status == ApprovalStatus.PENDING


def test_pending_dedupe_and_executed_replay_protection(db):
    candidate, job, _ = _pair(db)
    first = _propose_move(db, candidate, job)
    db.commit()

    same, created = approvals.create_or_get_request(
        db,
        conversation_id=None,
        tool_name="update_pipeline",
        args={"candidate_id": candidate.id, "job_id": job.id, "to_stage": "INTERVIEW"},
        summary="Move (duplicate proposal).",
    )
    assert not created and same.id == first.id  # no duplicate pending

    approvals.approve(db, first.id)
    db.commit()
    executed_again, created = approvals.create_or_get_request(
        db,
        conversation_id=None,
        tool_name="update_pipeline",
        args={"candidate_id": candidate.id, "job_id": job.id, "to_stage": "INTERVIEW"},
        summary="Move (post-execution proposal).",
    )
    assert not created and executed_again.status == ApprovalStatus.EXECUTED


def test_failed_execution_is_recorded_and_does_not_mutate(db):
    candidate, job, application = _pair(db)
    application.stage = "INTERVIEW"  # already there
    db.commit()

    request, _ = approvals.create_or_get_request(
        db,
        conversation_id=None,
        tool_name="update_pipeline",
        args={"candidate_id": candidate.id, "job_id": job.id, "to_stage": "INTERVIEW"},
        summary="Move to the same stage (will fail safely).",
    )
    db.commit()
    with pytest.raises(AppError):
        approvals.approve(db, request.id)
    db.commit()
    db.refresh(request)
    assert request.status == ApprovalStatus.FAILED
    assert request.error_code  # a real error code, no false success
    assert _stage_moved_events(db) == 0


def test_reject_only_pending(db):
    candidate, job, _ = _pair(db)
    request = _propose_move(db, candidate, job)
    db.commit()
    approvals.approve(db, request.id)
    db.commit()
    with pytest.raises(AppError):
        approvals.reject(db, request.id)
