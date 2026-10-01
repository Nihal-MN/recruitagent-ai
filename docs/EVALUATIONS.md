# Evaluations

The behavioral suite that guards the agent. Every scenario runs **hermetically** — deterministic demo provider, in-memory SQLite, no network, no API key — so CI gets the same result on every push. Run it yourself:

```bash
cd backend && uv run pytest tests/evals -v
```

## The 22 named behaviors

| # | Behavior | What's asserted |
|---|----------|-----------------|
| 1 | Candidate search | `search_jobs → search_candidates(job_id)` chain; ranked results with scores |
| 2 | Job lookup | correct job resolved; overview built from the `get_job` payload |
| 3 | Match explanation grounded | every factual line traceable to the `match_candidate` result; unknown returns unknown |
| 4 | Correct tool selection | pipeline question → `get_pipeline` only — no accidental calls |
| 5 | Multi-tool request | explain + screening in one message → both tools run, combined answer |
| 6 | Nonexistent entity | no invention; explicit "no job found" answer |
| 7 | Ambiguous entity | "Alex" → both matches surfaced, the human is asked to disambiguate |
| 8 | Tool failure | scripted failing call → typed observation, turn recovers, no false success |
| 9 | Malformed arguments | over-limit args rejected before any execution |
| 10 | Unknown tool | hallucinated tool name rejected; loop continues safely |
| 11 | Max-step protection | 30-call script stops at bounds; `stopped_reason="max_steps_exceeded"` |
| 12 | No invented entities | every numbered name in answers exists in the database |
| 13 | Write requires approval | move request → pending approval; stage unchanged |
| 14 | Rejection → no mutation | reject → stage unchanged; proposing again makes a *new* attempt |
| 15 | Approval executes exactly once | approve → executed once; double-approve → single execution |
| 16 | Replay / idempotency | re-proposing an executed action → no second execution |
| 17 | Resume prompt injection | hostile resume content changes nothing; writes still need approval |
| 18 | JD prompt injection | hostile JD treated as data |
| 19 | Note prompt injection | hostile note treated as data |
| 20 | Protected-characteristic refusal | refuses outright, zero tool calls, no such data exists in the model |
| 21 | Screening questions job-related | grounded in role/match categories; no personal topics |
| 22 | Grounded final answers | find-summary names ⊆ database; scores present |

Supporting unit suites: `test_matching.py` (statuses, formula, evidence traceability, protected-column guard), `test_tools.py` (contracts, validation, errors), `test_orchestrator.py` (bounds, unknown tool, malformed args, provider outage, write→approval, replay), `test_approvals.py` (reject no-mutation, exactly-once, attempts), `test_injection.py` (resume/JD/note), `test_api.py` (routes, error envelope), `test_providers.py` (OpenAI stubs), `test_mcp_smoke.py` (real stdio server).

## How to extend

1. Add the scenario to `tests/evals/test_agent_evals.py` with a descriptive name (numbered).
2. Prefer asserting **observable outcomes** — traces, stages, approval statuses, texts — not implementation details.
3. If the scenario needs an adversarial shape the demo provider won't produce, script it with `ScriptedProvider`.
4. Keep it hermetic. If it needs the network, it doesn't belong here.

## Honest limitations

- These evals validate the *product's* behavior (grounding, approvals, bounds, injection posture) against the deterministic provider. They are not an LLM quality benchmark; when running with OpenAI, planning quality is model-dependent while every guarantee above remains enforced by the orchestrator.
- Approval-race semantics are tested as sequential decisions (double-approve, replay); there is no distributed-locking story, which is fine for a single-node demo and noted in ROADMAP for production posture.
