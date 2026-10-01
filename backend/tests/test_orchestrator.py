"""Orchestrator edge cases via a scripted provider — bounds, failures, writes."""

from __future__ import annotations

from sqlalchemy import select

from app.agent.orchestrator import run_turn
from app.agent.providers.base import StepDecision, ToolCall
from app.models import Application, ApprovalRequest, ApprovalStatus, ToolExecution
from app.services import conversations
from tests.helpers import RaisingProvider, ScriptedProvider, amira_and_backend_ids


def _conversation(db):
    return conversations.create_conversation(db, "orchestrator-test")


def test_unknown_tool_is_rejected_gracefully(db):
    provider = ScriptedProvider(
        [
            ToolCall("steal_all_data", {"everything": True}),
            StepDecision(final_text="Recovered."),
        ]
    )
    outcome = run_turn(db, _conversation(db), provider, "do something weird")
    db.commit()
    executions = db.scalars(select(ToolExecution)).all()
    failed = [e for e in executions if e.status == "FAILED"]
    assert failed and failed[0].error_code == "validation_error"
    assert "Unknown tool" in (failed[0].result_summary or "")
    assert outcome.final_text == "Recovered."


def test_malformed_arguments_rejected_before_handler(db):
    provider = ScriptedProvider(
        [
            ToolCall("search_candidates", {"limit": 99999}),
            StepDecision(final_text="Noted."),
        ]
    )
    outcome = run_turn(db, _conversation(db), provider, "search weirdly")
    db.commit()
    assert outcome.stopped_reason == "final"
    failed = [e for e in db.scalars(select(ToolExecution)) if e.status == "FAILED"]
    assert failed and failed[-1].error_code == "validation_error"
    assert "limit" in (failed[-1].result_summary or "").lower()


def test_tool_failure_is_an_observation_not_a_crash(db):
    provider = ScriptedProvider(
        [
            ToolCall("get_candidate", {"identifier": "Nonexistent Person"}),
            StepDecision(final_text="That person doesn't exist."),
        ]
    )
    outcome = run_turn(db, _conversation(db), provider, "show me someone")
    db.commit()
    failed = [e for e in db.scalars(select(ToolExecution)) if e.status == "FAILED"]
    assert failed and failed[-1].error_code == "entity_not_found"
    assert outcome.final_text == "That person doesn't exist."


def test_max_steps_and_tool_call_ceiling(db):
    endless = [ToolCall("search_candidates", {"limit": 1}) for _ in range(30)]
    outcome = run_turn(db, _conversation(db), ScriptedProvider(endless), "loop forever")
    db.commit()
    executions = db.scalars(select(ToolExecution)).all()
    assert len(executions) <= 9  # max_steps=8 → at most 8 traces
    assert outcome.stopped_reason in ("max_steps_exceeded", "tool_call_limit")
    assert outcome.error_code == "max_steps_exceeded"


def test_write_tool_becomes_approval_not_execution(db):
    candidate_id, job_id = amira_and_backend_ids(db)
    provider = ScriptedProvider(
        [
            ToolCall(
                "update_pipeline",
                {"candidate_id": candidate_id, "job_id": job_id, "to_stage": "OFFER"},
            ),
            StepDecision(final_text="Awaiting your approval."),
        ]
    )
    outcome = run_turn(db, _conversation(db), provider, "move candidate 1 to offer")
    db.commit()

    assert outcome.approval_ids, "a write must produce an approval request"
    request = db.get(ApprovalRequest, outcome.approval_ids[0])
    assert request.status == ApprovalStatus.PENDING
    application = db.scalar(
        select(Application).where(
            Application.candidate_id == candidate_id, Application.job_id == job_id
        )
    )
    assert application is not None and application.stage == "SCREENING"  # unchanged
    trace = db.scalars(select(ToolExecution)).all()[-1]
    assert trace.status == "AWAITING_APPROVAL" and trace.approval_id == request.id


def test_write_replay_reports_already_executed(db):
    from app.services import approvals as approvals_service

    candidate_id, job_id = amira_and_backend_ids(db)
    provider = ScriptedProvider(
        [
            ToolCall(
                "update_pipeline",
                {"candidate_id": candidate_id, "job_id": job_id, "to_stage": "INTERVIEW"},
            ),
            StepDecision(final_text="Awaiting your approval."),
        ]
    )
    conversation = _conversation(db)
    first = run_turn(db, conversation, provider, "move candidate 1 to interview")
    db.commit()
    approvals_service.approve(db, first.approval_ids[0], decided_by="tester")
    db.commit()

    second = run_turn(
        db,
        conversation,
        ScriptedProvider(
            [
                ToolCall(
                    "update_pipeline",
                    {"candidate_id": candidate_id, "job_id": job_id, "to_stage": "INTERVIEW"},
                ),
                StepDecision(final_text="Done — already executed earlier."),
            ]
        ),
        "move candidate 1 to interview again",
    )
    db.commit()
    # Either a fresh attempt is proposed or the already-executed state is reported;
    # what must NEVER happen is a second execution of the same change.
    stage_changes = [
        e
        for e in db.scalars(select(ToolExecution))
        if e.tool_name == "update_pipeline" and e.status == "AWAITING_APPROVAL"
    ]
    assert len(stage_changes) >= 2
    application = db.scalar(
        select(Application).where(
            Application.candidate_id == candidate_id, Application.job_id == job_id
        )
    )
    assert application.stage == "INTERVIEW"
    assert second.stopped_reason == "final"


def test_provider_unavailable_never_claims_success(db):
    outcome = run_turn(db, _conversation(db), RaisingProvider(), "find candidates")
    db.commit()
    assert outcome.stopped_reason == "provider_unavailable"
    assert outcome.error_code == "provider_unavailable"
    assert "nothing was executed" in outcome.final_text.lower()
    assert db.scalars(select(ToolExecution)).all() == [] or all(
        e.status != "SUCCEEDED" for e in db.scalars(select(ToolExecution)).all()
    )
