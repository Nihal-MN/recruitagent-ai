"""The bounded agent loop.

User message → provider decides → typed tool call → schema validation →
authorization/approval policy → execution → safe trace event → observation →
… → grounded final response.

Guarantees enforced HERE (not in prompts, not in the UI):

- step and tool-call ceilings;
- unknown tools and malformed arguments never reach any handler;
- write tools never execute in the loop — they become ApprovalRequests;
- failures become observations, never false success claims;
- identifiers ("this candidate") resolve only through tool results.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.providers.base import AgentState, Observation, Provider
from app.core.errors import AppError, ErrorCode
from app.models import (
    AgentConversation,
    ApprovalStatus,
    ToolExecution,
    ToolExecutionStatus,
)
from app.services import approvals as approvals_service
from app.services import conversations as conversations_service
from app.tools.executor import execute_tool
from app.tools.registry import get_tool, sanitize_args

PRIOR_CONTEXT_LIMIT = 6  # grounded context keys carried from earlier turns


@dataclass
class RunOutcome:
    final_text: str
    stopped_reason: str  # "final" | "max_steps_exceeded" | "tool_call_limit"
    tool_execution_ids: list[int] = field(default_factory=list)
    approval_ids: list[int] = field(default_factory=list)
    error_code: str | None = None


def _prior_observations(db: Session, conversation_id: int) -> list[Observation]:
    """Rebuild grounded context (ids only) from earlier executions in this conversation."""
    rows = list(
        db.scalars(
            select(ToolExecution)
            .where(ToolExecution.conversation_id == conversation_id)
            .order_by(ToolExecution.id.desc())
            .limit(PRIOR_CONTEXT_LIMIT)
        )
    )
    observations: list[Observation] = []
    for row in reversed(rows):
        observations.append(
            Observation(
                tool=row.tool_name,
                ok=row.status == ToolExecutionStatus.SUCCEEDED,
                summary=row.result_summary or "",
                data=None,
                error_code=row.error_code,
                args=dict(row.args_json or {}),
                meta=dict(row.meta_json or {}),
            )
        )
    return observations


def _context_meta(args: dict, result: dict | None) -> dict:
    """Extract only grounded context keys — never bodies, never PII dumps."""
    meta: dict = {}
    for key in ("job_id", "candidate_id"):
        if args.get(key):
            meta[key] = args[key]
    data = result or {}
    for key in ("job_id", "candidate_id", "application_id"):
        if data.get(key):
            meta[key] = data[key]
    if data.get("id") and data.get("full_name"):
        meta["candidate_id"] = data["id"]  # get_candidate result
    candidates = data.get("candidates")
    if candidates:
        meta["top_candidate_id"] = candidates[0]["id"]
        meta["result_count"] = len(candidates)
    jobs = data.get("jobs")
    if jobs:
        meta["top_job_id"] = jobs[0]["id"]
        meta["result_count"] = len(jobs)
    return meta


def _approval_summary(db: Session, tool_name: str, params: dict) -> str:
    return approvals_service.describe_action(db, tool_name, params)


def _trace(
    db: Session,
    conversation_id: int,
    step: int,
    tool_name: str,
    kind: str,
    status: str,
    *,
    args: dict | None = None,
    summary: str | None = None,
    error_code: str | None = None,
    duration_ms: int | None = None,
    approval_id: int | None = None,
    meta: dict | None = None,
) -> ToolExecution:
    row = ToolExecution(
        conversation_id=conversation_id,
        step_number=step,
        tool_name=tool_name,
        tool_kind=kind,
        args_json=args,
        status=status,
        error_code=error_code,
        result_summary=summary,
        duration_ms=duration_ms,
        approval_id=approval_id,
        meta_json=meta,
    )
    db.add(row)
    db.flush()
    return row


def run_turn(
    db: Session,
    conversation: AgentConversation,
    provider: Provider,
    user_text: str,
) -> RunOutcome:
    from app.core.config import get_settings

    settings = get_settings()
    max_steps = max(1, settings.agent_max_steps)
    max_tool_calls = max(1, settings.agent_max_tool_calls)

    conversations_service.append_message(db, conversation, "user", user_text)
    history = [
        {"role": m.role, "content": m.content}
        for m in conversations_service.recent_messages(db, conversation.id, limit=10)
        if m.role in ("user", "assistant")
    ][:-1]  # exclude the message we just appended (it is passed separately)

    state = AgentState(
        user_message=user_text,
        history=history,
        observations=[],
        prior_observations=_prior_observations(db, conversation.id),
        max_steps=max_steps,
        max_tool_calls=max_tool_calls,
    )

    outcome = RunOutcome(final_text="", stopped_reason="final")
    tool_calls_made = 0

    for step in range(1, max_steps + 1):
        state.step = step
        state.tool_calls_made = tool_calls_made
        try:
            decision = provider.next_step(state)
        except AppError as exc:
            outcome.final_text = (
                f"I couldn't reach the AI provider ({exc.code.value}). {exc.message} "
                "Nothing was executed — try again shortly."
            )
            outcome.stopped_reason = "provider_unavailable"
            outcome.error_code = exc.code.value
            break
        except Exception:
            outcome.final_text = (
                "The provider failed unexpectedly. Nothing was executed — your data is unchanged."
            )
            outcome.stopped_reason = "provider_unavailable"
            outcome.error_code = ErrorCode.provider_unavailable.value
            break

        if decision.final_text is not None:
            outcome.final_text = decision.final_text.strip()
            outcome.stopped_reason = "final"
            break

        call = decision.tool_call
        if call is None:  # defensive: provider contract violated
            outcome.final_text = "I couldn't continue safely. Please rephrase the request."
            outcome.stopped_reason = "final"
            outcome.error_code = ErrorCode.tool_failed.value
            break

        spec = get_tool(call.name)
        if spec is None:
            observation = Observation(
                tool=call.name,
                ok=False,
                summary=f"Unknown tool '{call.name}' was rejected. Nothing happened.",
                error_code=ErrorCode.validation_error.value,
            )
            row = _trace(
                db,
                conversation.id,
                step,
                call.name,
                "unknown",
                ToolExecutionStatus.FAILED,
                error_code=ErrorCode.validation_error.value,
                summary=observation.summary,
            )
            outcome.tool_execution_ids.append(row.id)
            state.observations.append(observation)
            continue

        if tool_calls_made >= max_tool_calls:
            observation = Observation(
                tool=call.name,
                ok=False,
                summary="Tool-call limit for this request reached — stopping safely.",
                error_code=ErrorCode.max_steps_exceeded.value,
            )
            row = _trace(
                db,
                conversation.id,
                step,
                call.name,
                spec.kind,
                ToolExecutionStatus.FAILED,
                error_code=ErrorCode.max_steps_exceeded.value,
                summary=observation.summary,
            )
            outcome.tool_execution_ids.append(row.id)
            state.observations.append(observation)
            outcome.stopped_reason = "tool_call_limit"
            continue

        # Validate BEFORE any policy or execution — malformed args never touch handlers.
        try:
            params = spec.input_model.model_validate(call.args)
        except ValidationError as exc:
            first = exc.errors()[0] if exc.errors() else {}
            detail = (
                f"{'.'.join(str(p) for p in first.get('loc', ()))}: {first.get('msg', 'invalid')}"
            )
            observation = Observation(
                tool=call.name,
                ok=False,
                summary=f"Invalid arguments for {call.name} ({detail}). Nothing happened.",
                error_code=ErrorCode.validation_error.value,
            )
            row = _trace(
                db,
                conversation.id,
                step,
                call.name,
                spec.kind,
                ToolExecutionStatus.FAILED,
                error_code=ErrorCode.validation_error.value,
                summary=observation.summary,
                args=None,
            )
            outcome.tool_execution_ids.append(row.id)
            state.observations.append(observation)
            continue

        tool_calls_made += 1

        # ── policy: consequential writes become approval requests ───────────
        if spec.requires_approval:
            summary = _approval_summary(db, spec.name, params.model_dump(exclude_none=True))
            request, created = approvals_service.create_or_get_request(
                db,
                conversation_id=conversation.id,
                tool_name=spec.name,
                args=params.model_dump(exclude_none=True),
                summary=summary,
            )
            if created:
                observation = Observation(
                    tool=spec.name,
                    ok=True,
                    summary=summary,
                    error_code=ErrorCode.approval_required.value,
                    args=sanitize_args(spec, params),
                    meta={
                        "approval_id": request.id,
                        "approval_status": request.status,
                    },
                    call_ref=call.ref,
                )
            else:
                if request.status == ApprovalStatus.EXECUTED:
                    observation = Observation(
                        tool=spec.name,
                        ok=False,
                        summary=(
                            "This exact action was already approved and executed — "
                            "not doing it again."
                        ),
                        error_code=ErrorCode.policy_blocked.value,
                        args=sanitize_args(spec, params),
                        meta={"approval_id": request.id, "approval_status": request.status},
                        call_ref=call.ref,
                    )
                elif request.status == ApprovalStatus.PENDING:
                    observation = Observation(
                        tool=spec.name,
                        ok=True,
                        summary=f"Identical approval #{request.id} is already pending. {summary}",
                        error_code=ErrorCode.approval_required.value,
                        args=sanitize_args(spec, params),
                        meta={"approval_id": request.id, "approval_status": request.status},
                        call_ref=call.ref,
                    )
                elif request.status == ApprovalStatus.REJECTED:
                    observation = Observation(
                        tool=spec.name,
                        ok=False,
                        summary="This exact action was rejected earlier — propose changes "
                        "or a different action.",
                        error_code=ErrorCode.approval_rejected.value,
                        args=sanitize_args(spec, params),
                        meta={"approval_id": request.id, "approval_status": request.status},
                        call_ref=call.ref,
                    )
                else:
                    observation = Observation(
                        tool=spec.name,
                        ok=False,
                        summary=f"Approval #{request.id} already exists in state {request.status}.",
                        error_code=ErrorCode.policy_blocked.value,
                        args=sanitize_args(spec, params),
                        meta={"approval_id": request.id, "approval_status": request.status},
                        call_ref=call.ref,
                    )
            row = _trace(
                db,
                conversation.id,
                step,
                spec.name,
                spec.kind,
                ToolExecutionStatus.AWAITING_APPROVAL,
                args=sanitize_args(spec, params),
                summary=observation.summary,
                approval_id=request.id,
                meta=observation.meta,
            )
            outcome.tool_execution_ids.append(row.id)
            outcome.approval_ids.append(request.id)
            state.observations.append(observation)
            continue

        # ── read / generation: execute immediately ──────────────────────────
        started = time.monotonic()
        executed = execute_tool(
            db, spec.name, params.model_dump(exclude_none=True), _ctx(conversation)
        )
        duration_ms = executed.duration_ms or int((time.monotonic() - started) * 1000)
        if executed.ok and executed.result is not None:
            summary = spec.summarizes_as(executed.result)
            meta = _context_meta(params.model_dump(exclude_none=True), executed.result)
            observation = Observation(
                tool=spec.name,
                ok=True,
                summary=summary,
                data=executed.result,
                args=sanitize_args(spec, params),
                meta=meta,
                call_ref=call.ref,
            )
            row = _trace(
                db,
                conversation.id,
                step,
                spec.name,
                spec.kind,
                ToolExecutionStatus.SUCCEEDED,
                args=sanitize_args(spec, params),
                summary=summary,
                duration_ms=duration_ms,
                meta=meta,
            )
        else:
            observation = Observation(
                tool=spec.name,
                ok=False,
                summary=executed.error_message or "The tool failed.",
                error_code=executed.error_code,
                args=sanitize_args(spec, params),
                call_ref=call.ref,
            )
            row = _trace(
                db,
                conversation.id,
                step,
                spec.name,
                spec.kind,
                ToolExecutionStatus.FAILED,
                args=sanitize_args(spec, params),
                summary=observation.summary,
                error_code=executed.error_code,
                duration_ms=duration_ms,
            )
        outcome.tool_execution_ids.append(row.id)
        state.observations.append(observation)

    else:
        # Loop exhausted without a final answer.
        outcome.final_text = (
            "I reached my step limit for this request. Here's what I completed so far — "
            "ask me to continue and I'll pick up from the tool trail."
        )
        outcome.stopped_reason = "max_steps_exceeded"
        outcome.error_code = ErrorCode.max_steps_exceeded.value

    conversations_service.append_message(db, conversation, "assistant", outcome.final_text)
    return outcome


def _ctx(conversation: AgentConversation):
    from app.tools.registry import ToolContext

    return ToolContext(conversation_id=conversation.id, actor="agent")
