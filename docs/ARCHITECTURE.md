# Architecture

RecruitAgent AI is a small, complete system: one FastAPI backend, one Next.js frontend, PostgreSQL, and an agent loop that is deliberately the most auditable part of the whole stack.

## Process view

```
┌────────────┐   HTTP    ┌──────────────────────────── FastAPI ────────────────────────────┐
│  Next.js   │ ────────► │  /api/v1: conversations · approvals · activity · traces ·       │
│  console   │           │           candidates · jobs · pipeline · health                 │
└────────────┘           │                                                                  │
                         │  Orchestrator ── Provider (demo | OpenAI)                        │
                         │      │            designs the next step only                     │
                         │      ▼                                                           │
                         │  Tool Registry (10 tools, strict Pydantic contracts)             │
                         │      │  reads/generations: execute now                           │
                         │      │  writes: → ApprovalRequest (PENDING, no execution)        │
                         │      ▼                                                           │
                         │  Services (matching, pipeline, notes, search, generation)        │
                         └───────────────┬──────────────────────────────┬──────────────────┤
                                         │                              │
                                  PostgreSQL 16                  Tool Trace + Activity
                                  (12 tables)                    (append-only audit)
```

## The agent loop (backend/app/agent/orchestrator.py)

One `run_turn` handles a user message:

1. Persist the user message; rebuild a bounded context (recent messages + recent tool observations with grounded ids).
2. Loop up to **max_steps** (8), with at most **max_tool_calls** (6):
   - `provider.next_step(state)` returns a typed decision: a tool call or a final answer.
   - Unknown tool → rejected with a structured `validation_error` observation.
   - Arguments are re-validated against the tool's Pydantic model — malformed args never reach a handler.
   - `write` tools → an `ApprovalRequest` is created (arguments validated first, summary generated), a trace row is written with status `AWAITING_APPROVAL`, and the observation tells the model the action awaits a human.
   - Everything else executes through the single executor path, timed and traced.
   - Every failure becomes an observation (`entity_not_found`, `ambiguous_entity`, `tool_failed`, …) — the loop never crashes, and the model must adapt to what actually happened.
3. Persist the final answer. The outcome carries `stopped_reason` — `final`, `max_steps_exceeded`, or `provider_unavailable` — which the UI and tests surface honestly.

Providers design steps; they are never able to execute anything, skip validation, or touch the database. All policy lives in the loop.

## Data model (12 tables)

`candidates`, `candidate_skills`, `candidate_experiences`, `jobs`, `job_requirements`, `applications`, `candidate_notes`, `agent_conversations`, `agent_messages`, `tool_executions`, `approval_requests`, `activity_events`.

Notes:

- `applications.stage` is a real pipeline: NEW → SCREENING → SHORTLISTED → INTERVIEW → OFFER → HIRED (or REJECTED).
- `tool_executions.args_json` is sanitized (truncated fields, no bodies); `meta_json` carries only grounded context ids.
- `approval_requests.idempotency_key` is unique per `(conversation, tool, canonical args, attempt)` — the backbone of exactly-once.
- Nothing anywhere stores protected characteristics; `tests/test_matching.py::test_no_protected_columns_in_schema` enforces it structurally.

## Matching (backend/app/services/matching.py)

Deterministic and explainable — the LLM is never the ranker:

- Each job requirement (must-have / preferred; skill, experience, domain, location, education, other) is evaluated to `met | partial | missing | unknown` with a written reason.
- Evidence is quoted from stored fields — skill evidence lines trace back to the exact `resume_text` line (`233/233`-style traceability is asserted for the seeded dataset in tests).
- Related-skill families give honest `partial` credit (React ↔ Vue), and years compare numerically with a partial band.
- Score = weighted rollup (must 0.6, preferred 0.2, experience 0.1, domain 0.1), re-normalized over the knowable components, and the formula is returned with every result.

## Frontend

Next.js App Router, server-light client components, a typed API client (`src/lib/api.ts`) that parses the backend's structured error envelope, and a safe mini-markdown renderer (React elements only — no `dangerouslySetInnerHTML`, asserted in tests).

## Bounds & configuration

Everything in `backend/app/core/config.py`, env-driven: DB URL (PostgreSQL in Docker, SQLite fallback for dev), `AI_PROVIDER`, `OPENAI_MODEL`, CORS origins, `AGENT_MAX_STEPS`, `AGENT_MAX_TOOL_CALLS`.
