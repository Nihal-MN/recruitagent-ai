# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows [SemVer](https://semver.org/).

## [0.1.0] — 2026-10-01

First public release: a complete, keyless-runnable human-in-the-loop recruiting agent.

### Added

**Agent core**
- Bounded orchestrator loop with typed observations, per-turn step and tool-call ceilings, and honest `stopped_reason` reporting.
- Provider abstraction with two implementations: a deterministic demo agent (no API key; powers the demo and the eval suite) and a live OpenAI tool-calling provider (Responses API + structured outputs), selected via `AI_PROVIDER=auto`.
- Strict Pydantic contracts for every tool input/output; the agent cannot call anything outside the ten registered tools.

**Tools (10)**
- Reads: `search_candidates` (with match-ranked mode by job), `get_candidate`, `search_jobs`, `get_job`, `match_candidate`, `get_pipeline`.
- Generations: `generate_screening_questions`, `draft_outreach` (grounded, gap-aware).
- Controlled writes: `update_pipeline`, `add_candidate_note` — both approval-gated.

**Approvals & audit**
- Backend-enforced approval flow (`PENDING → APPROVED → EXECUTING → EXECUTED | FAILED`), exactly-once execution, rejection with zero mutation, attempt-scoped idempotency for re-proposals, and an append-only activity log.

**Explainable matching**
- Deterministic requirement-by-requirement matching (met/partial/missing/unknown) with quoted evidence traceable to stored resume text, a documented weighted formula, and related-skill partial credit.

**MCP**
- Stdio MCP server exposing six read tools plus a proposal-only `propose_pipeline_update`; write execution is impossible over MCP. End-to-end smoke test included.

**API & UI**
- REST surface: conversations/agent turns, approvals, activity, tool trace, candidates, jobs, pipeline, health — with a structured error envelope.
- Next.js console: Agent Chat with live tool-trace panel, Tool Trace, Candidates (+detail with evidence), Jobs (+requirements), Approvals, Activity timeline, System Health (explicit demo/live AI mode).

**Quality**
- 74 backend tests including a 23-scenario eval suite (22 planned + 1 regression): grounding, entity errors, malformed args, unknown tools, step bounds, approvals lifecycle, replay/idempotency, resume/JD/note prompt injection, protected-characteristic refusal, MCP stdio smoke.
- Frontend unit tests (markdown safety, API client, formatters).
- CI: backend lint+tests, frontend lint/typecheck/tests/build, Docker image build. Dependabot configured.
- Synthetic standalone dataset: 20 candidates, 5 jobs, pipeline states, notes (including a live injection example).

[0.1.0]: https://github.com/<you>/recruitagent-ai/releases/tag/v0.1.0
