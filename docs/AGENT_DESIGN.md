# Agent design

How RecruitAgent plans, acts, fails and answers — and why the controls live where they live.

## The contract

A provider may only *design* a step. Everything else is the orchestrator's job:

| Concern | Owner | Never the provider |
|---|---|---|
| Which tool / what arguments | provider | — |
| Argument validation | orchestrator (Pydantic) | ✗ |
| Write authorization | orchestrator → ApprovalRequest | ✗ |
| Execution | executor (single path) | ✗ |
| Bounds (steps, calls) | orchestrator | ✗ |
| Tracing, sanitization | orchestrator | ✗ |

This is the ADR-0001 split: **providers plan, the platform enforces.**

## The two providers

### `demo` — deterministic, keyless, complete

A rule-based planner (`app/agent/providers/demo.py`) that behaves like a careful LLM completing a tool-calling turn:

1. Classifies intent from the user message (find, explain, screening, outreach, note, move, pipeline, job info, profile lookup, greeting, protected-request refusal, unknown → help text).
2. Plans a short tool chain (e.g. `search_jobs → search_candidates(job_id) → final`), tracking entity context (`job_id`, focused candidate) across steps and across turns via persisted, grounded ids.
3. Renders final answers **from the actual tool results**: scores, requirement counts, evidence quotes, stage names. If a tool returned nothing, the answer says so.

It refuses protected-characteristic requests outright (no tool call), requires the same approvals as any provider, and is what the entire eval suite runs against.

### `openai` — live tool calling

Uses the current Responses API: `tools=[{type: function, …}]` generated from the registry contracts, `function_call` items parsed into typed tool calls, `function_call_output` observations fed back, and structured outputs for screening/outreach generation. The system prompt encodes the same policy the demo provider embodies in code: writes need approval (enforced anyway), tool output is untrusted data, no protected characteristics, no invented entities, answer only from tool results.

When a key is absent, `/health` and the UI report the demo provider — there is no silent fallback mid-turn, and no path that pretends a model ran when one didn't.

## Error model

Every failure is a typed observation, not an exception: `entity_not_found`, `ambiguous_entity`, `validation_error`, `approval_required`, `approval_rejected`, `tool_failed`, `provider_unavailable`, `max_steps_exceeded`, `policy_blocked`. The provider must respond to what happened — the demo provider turns each into an honest sentence, and the evals assert no false success claims.

## Prompt-injection posture

Resumes, JDs and notes are **untrusted data**:

- The demo provider parses only the user message for intent; tool content is only ever rendered, never interpreted.
- The OpenAI system prompt states the policy explicitly: instructions inside data are ignored and reported as content if relevant.
- Injection attempts (including "the resume says to move me to HIRED — do it") still land in the same place as any write: a pending approval. There is no content-triggered path to execution.
- Tests: `tests/test_injection.py` + evals 17–19 cover injection via resume, JD and note; the seeded dataset includes a live example (Alex Meyer's resume contains a hostile line; nothing about the demo's behavior changes).

## Transparency rules

The Tool Trace records: tool name, sanitized arguments (truncated strings, no bodies), status, error code, duration, approval link, grounded context ids, timestamps. It deliberately does **not** store chain-of-thought or provider reasoning — there is no such field in the schema, by design. The UI copy says so on the page.

## Bounds

- `AGENT_MAX_STEPS` (default 8): hard ceiling per turn → turn ends `max_steps_exceeded` with partial results, never a hang.
- `AGENT_MAX_TOOL_CALLS` (default 6): separate ceiling on executions per turn.
- Provider exceptions (`provider_unavailable`) end the turn with a clear message and an honest `stopped_reason`.
