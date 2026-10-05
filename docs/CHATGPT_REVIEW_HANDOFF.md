# ChatGPT Review Handoff — RecruitAgent AI

**Purpose:** an independent reviewer validates the claims in this repo against the actual code, tests, and runtime behavior — including a fresh verification pass whose exact commands and results are recorded below.
**Review pass date:** 2026-10-05 · **Repo:** [github.com/Nihal-MN/recruitagent-ai](https://github.com/Nihal-MN/recruitagent-ai) · **Branch:** `main` · **Code tip verified:** `85fb3a2` (all subsequent commits in this pass are documentation-only)

---

## §1 What was built and the promises made

An open-source, human-in-the-loop recruiting operations agent:

1. Bounded agent loop with strict tool contracts and typed error observations.
2. Consequential writes (pipeline move, note) can never execute from the agent loop — only via a human approval, **exactly once**.
3. A deterministic demo provider (no API key) that drives the same loop, tools, approvals and traces; OpenAI tool calling available behind one env var.
4. An MCP server exposing reads + a proposal-only write.
5. A 23-scenario eval suite incl. prompt-injection and idempotency; hermetic in CI.
6. Full UI: agent chat + live trace, trace page, candidates, jobs, approvals, activity, health.

## §2 How to verify (15 minutes)

```bash
git clone https://github.com/Nihal-MN/recruitagent-ai.git && cd recruitagent-ai
docker compose up --build -d
docker compose exec api python -m app.seed
cd backend && uv run pytest -v          # 74 tests incl. evals + MCP smoke
```

Then in the UI (http://localhost:3000 — or the port set in `.env`):
- "Find candidates for the Senior Backend Engineer role" → ranked, scored list; trace panel populates.
- "Why does this candidate match?" → requirement-by-requirement with quoted evidence.
- "Move this candidate to INTERVIEW" → pending approval; **nothing changes**. Reject → still nothing (Activity confirms). Propose again → new approval; approve → stage moves once; approving again does not re-execute.
- The hostile line seeded in Alex Meyer's resume ("…move me to HIRED") → acting on it still just files an approval; nothing auto-executes.

## §3 Verification receipt — executed 2026-10-05, actual results only

| # | Check | Command | Result |
|---|-------|---------|--------|
| 1 | Backend lint | `cd backend && uv run ruff check app tests` | **All checks passed** |
| 2 | Backend full suite | `uv run pytest` | **74 passed** in 3.32s |
| 3 | Named agent eval suite | `uv run pytest tests/evals` | **23 passed** in 0.77s |
| 4 | MCP smoke (real stdio server) | `uv run pytest tests/test_mcp_smoke.py` | **1 passed** in 3.12s |
| 5 | Frontend unit tests | `cd frontend && npm test` | **11 passed** (3 files) |
| 6 | Frontend lint | `npm run lint` | clean |
| 7 | Frontend typecheck | `npm run typecheck` | clean |
| 8 | Frontend production build | `npm run build` | compiled successfully · 10 routes |
| 9 | Docker build (current tree) | `docker compose build` | api + web images built |
| 10 | Docker runtime | `docker compose up -d` + health checks | api **healthy** · web HTTP **200** · provider `demo` · counts 20 candidates / 5 jobs / 13 applications |
| 11 | GitHub Actions (latest main) | `gh run list` | **CI: success**, **CodeQL: success** (runs `37222678267`, `37222678184`) |
| 12 | Screenshots | integrity script + visual spot-checks | **18/18 valid PNGs**; last `frontend/src` change (`715ee7e`) predates the captures and no UI code changed after them |
| 13 | Secrets / PII / TODO scan | `git grep` on final tree | no secrets, no real candidate data, no TODO/FIXME release blockers |
| 14 | Count consistency | grep of README/CHANGELOG/CONTRIBUTING/docs | all count references match §3 (one stale "73" in CONTRIBUTING fixed in this pass; frontend count "11" added to README/EVALS/CHANGELOG) |

Anything not verified in this pass is labeled as such in §10–§12. Nothing here is an estimate.

## §4 Claims → where to check them in code

| Claim | Where |
|---|---|
| Providers can only plan; the loop validates/authorizes/executes | `backend/app/agent/orchestrator.py`; ADR-0001 |
| Write tools never execute from the loop | `orchestrator.py`; `tests/test_orchestrator.py::test_write_tool_becomes_approval_not_execution` |
| Approval executes exactly once; replay is a no-op | `backend/app/services/approvals.py`; `tests/test_approvals.py`; evals 15–16 |
| Rejection = zero mutation | `tests/test_approvals.py::test_reject_causes_zero_mutation`; eval 14 |
| Unknown tool / malformed args rejected safely | `orchestrator.py`; evals 9–10 |
| Step/tool-call bounds honored | `orchestrator.py`; eval 11 (`AGENT_MAX_STEPS`, `AGENT_MAX_TOOL_CALLS`) |
| Matching deterministic + evidence-traceable | `backend/app/services/matching.py`; `tests/test_matching.py` |
| No protected characteristics stored | `tests/test_matching.py::test_no_protected_columns_in_schema` |
| Injection can't trigger writes (resume/JD/note) | `tests/test_injection.py`; evals 17–19; seeded hostile resume (Alex Meyer) |
| MCP cannot execute writes (proposal-only) | `backend/app/mcp_server.py`; ADR-0003; `tests/test_mcp_smoke.py` (DB-verified stage unchanged) |
| Trace stores no chain-of-thought | `tool_executions` schema has no reasoning field; UI copy on /trace |
| Grounded answers (no invented entities) | eval 12; demo provider renders only from tool data |
| OpenAI provider wiring (stub-tested, not live-tested) | `backend/app/agent/providers/openai_provider.py`; `tests/test_providers.py` |

## §5 Architecture & agent loop (summary)

`Next.js → FastAPI → Orchestrator → Provider(demo|openai) → Tool Registry → Services → PostgreSQL`

Per turn (`run_turn`): persist user message → loop up to 8 steps / 6 tool calls → provider returns a typed decision → unknown tools and malformed args become typed observations (`validation_error`) → write tools become `ApprovalRequest`s (args validated first; human-readable summary) → everything else executes through one executor path (timed, traced) → every failure is a typed observation, the loop never crashes → grounded final answer with an honest `stopped_reason` (`final` | `max_steps_exceeded` | `provider_unavailable`). Details: `docs/ARCHITECTURE.md`, `docs/AGENT_DESIGN.md`, ADR-0001.

## §6 Tools (10)

Reads: `search_candidates` (match-ranked mode with `job_id`), `get_candidate`, `search_jobs`, `get_job`, `match_candidate`, `get_pipeline`.
Generations: `generate_screening_questions`, `draft_outreach`.
Controlled writes (**both approval-gated**): `update_pipeline`, `add_candidate_note`.
Strict Pydantic contracts for every input/output (`backend/app/tools/contracts.py`); documented in `docs/TOOLS.md`.

## §7 Approval behavior (backend-enforced, not UI)

`PENDING → APPROVED → EXECUTING → EXECUTED | FAILED`, recorded with actor + timestamps. Idempotency keys are attempt-scoped `(conversation, tool, canonical args, attempt)`: identical PENDING proposals dedupe; an EXECUTED action refuses re-execution ("already executed"); a REJECTED one can be re-proposed as a new attempt, with the rejection preserved in history. Verified in this pass via tests + the live acceptance flow (reject → zero change; approve → one `stage_moved` event; replay approve → stored result, no second execution).

## §8 MCP status

`cd backend && python -m app.mcp_server` (stdio). Tools: 6 reads + `propose_pipeline_update` (creates a PENDING approval; mutates nothing). Write execution is not exposed — impossible over MCP (ADR-0003). The smoke test launches the real server as a subprocess and, via the official MCP client: lists 7 tools, calls reads, asserts over-limit args error, and DB-verifies the proposal created an approval with the stage unchanged. **Result: 1 passed (3.12s).**

## §9 Browser acceptance (performed 2026-10-01/02, screenshots in `docs/screenshots/`)

23-step scenario executed end-to-end on the Docker/PostgreSQL stack: chat find → grounded rankings (only seeded candidates) → tool trace inspection → evidence-quoted match explanation → screening questions (job-related only) → move request → **reject: DB-proven zero mutation** → re-propose → approve → **exactly-once DB-proven (1 stage_moved event; API replay safe)** → note workflow (approved, provenance `agent (approved by recruiter)`) → refresh/restart persistence → activity audit trail → hostile-resume injection attempt still gated (approval only; HIRED count stayed 0) → MCP smoke → full test suites → screenshots. Two real bugs were found and fixed during acceptance (note provenance label; explicit candidate names being ignored in favor of context) — both have regression tests (eval 23).

## §10 Docker verification

- CI docker job: **success** on the latest main run (builds both images from the pushed tree).
- Local this pass: `docker compose build` built api + web; `docker compose up -d` → api healthy, web HTTP 200, seeded counts correct, provider `demo`. Migrations run on container boot; seeding is opt-in (`python -m app.seed`).

## §11 Live vs stubbed OpenAI verification (honest labels)

- Implemented: Responses API tool calling (`tools=[…]` from registry contracts, `function_call`/`function_call_output` loop) + structured outputs for generation.
- Stub-tested: `tests/test_providers.py` exercises the exact SDK shapes with an injected client; provider errors map to `provider_unavailable`.
- **Not live-tested**: no API key was available in this environment. `/health` and the sidebar always report which provider actually ran; docs never blur the two. Treat live-provider behavior as "wiring verified, runtime unverified".

## §12 Known limitations

1. **No auth** — deliberately local/portfolio posture; documented in `SECURITY.md` + ROADMAP item #1.
2. OpenAI path not live-tested (§11).
3. Approval “concurrency”: sequential double-decisions and replays are tested; concurrent double-approve relies on a status check + unique key (single-node).
4. Demo provider handles the documented demo intents; unusual phrasings fall back to an honest help message rather than guessing.
5. Search is SQL-level (ILIKE + skill canonicalization); no embeddings (deliberate).
6. The demo dataset is synthetic by construction; do not load real candidate data.

## §13 Repo state & how to check it

- Branch `main`; code tip verified in this pass: **`85fb3a2`** (subsequent commits: documentation-only, including this handoff).
- Latest Actions run on main: **CI success + CodeQL success** (see §3 row 11). If that ever changes, treat the newest failing run as authoritative.
- Community profile: 100% (README, CoC, Contributing, License, issue/PR templates). Social preview verified live; announcement Discussion #7 pinned.

## §14 Reviewer checklist — try to break these

- [ ] Get any write to execute without an approval (API, MCP, chat phrasing).
- [ ] Replay an approval endpoint call after execution — confirm no second execution.
- [ ] Reject, then re-propose the same action — confirm a new pending request + intact history.
- [ ] Feed hostile text via resume, JD, note (and via chat itself).
- [ ] Ask for a nonexistent or ambiguous candidate/job — confirm no invention.
- [ ] Ask for protected-characteristic filtering — confirm refusal, zero tool calls.
- [ ] Verify `/health` matches the provider actually in use.
- [ ] Clean-clone + `docker compose up` + `uv run pytest` — all green, no network needed for tests.

## §15 Questions most wanted from this review

1. Any path — code, config, UI — by which a write executes without a recorded human approval?
2. Any failure mode that produces a *false success* claim to the user?
3. Is the injection posture airtight on the live-provider path, given it's prompt-enforced there (structural guarantees remain)?
4. Are the eval scenarios meaningful, or is a materially important behavior missing?
5. Anything in the docs that overclaims relative to the code?

## §16 What changed in this final pass (docs-only, no code changes)

- `CONTRIBUTING.md`: stale test count fixed (73 → 74).
- `README.md`, `docs/EVALUATIONS.md`, `CHANGELOG.md`: frontend test count (11) made explicit.
- This handoff: rewritten as the final review packet (previous pass content preserved in spirit; all counts re-verified by execution on 2026-10-05).
- No functional changes: no new tools, providers, agents, or features — per the release freeze.
