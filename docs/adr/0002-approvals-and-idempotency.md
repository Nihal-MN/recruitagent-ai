# ADR 0002 — Approvals are enforced in the backend, with exactly-once execution

**Status:** accepted

## Context

An AI recruiting agent that can move candidates through a pipeline or write notes is only trustworthy if a human decision gates every consequential write — and if the platform, not the prompt, enforces that gate. A second failure mode: retries (double-clicks, replayed requests) executing the same write twice.

## Decision

- The tool registry classifies every tool as `read`, `generation` or `write`.
- When the agent emits a `write` call, the orchestrator **does not execute it**. It validates the arguments, builds a human-readable summary (`describe_action`), and creates a `PENDING` `ApprovalRequest` with an idempotency key derived from `(conversation, tool, canonical args)`.
- Execution happens only through `approvals.approve()`. The lifecycle is `PENDING → APPROVED → EXECUTING → EXECUTED` (or `FAILED`), recorded with timestamps and actor.
- `approve()` on an `EXECUTED` request returns the stored result **without re-executing** — approval idempotency. A second decision on a decided request is refused.
- Rejecting executes nothing — zero mutation, by construction.
- A rejected attempt can be re-proposed later: the system creates a **new** request (attempt-scoped idempotency key), so history stays honest and users can change their minds.

## Consequences

- "The agent moved a candidate without us" is structurally impossible via the product's write path.
- Duplicate execution requires bypassing both a status check and a unique idempotency key.
- Approval history includes failed executions with error codes, which keeps the audit trail honest.

## Verification

`backend/tests/test_approvals.py`, `backend/tests/test_orchestrator.py`, and evals 13–16 cover: write → pending only; reject → no mutation; approve → executes once; double-approve → single execution; replay after execution → no-op.
