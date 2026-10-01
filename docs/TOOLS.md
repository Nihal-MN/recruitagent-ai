# Tools

The registry is the agent's entire capability surface — ten tools, strict contracts, explicit classification. Anything not here does not exist to the agent.

| # | Tool | Kind | Inputs (strict) | Returns |
|---|------|------|-----------------|---------|
| 1 | `search_candidates` | read | `query?`, `skill?`, `job_id?`, `limit≤20` | matches; with `job_id`, ranked by deterministic match score |
| 2 | `get_candidate` | read | `identifier` (id or name) | full profile + skills with evidence + applications + notes |
| 3 | `search_jobs` | read | `query?`, `limit≤20` | job summaries |
| 4 | `get_job` | read | `identifier` (id or title) | job + its requirements |
| 5 | `match_candidate` | read | `candidate_id`, `job_id` | requirement-by-requirement explainable match with quoted evidence |
| 6 | `get_pipeline` | read | `job_id?` | board grouped by stage with application/candidate/job refs |
| 7 | `generate_screening_questions` | generation | `candidate_id`, `job_id`, `count≤10` | job-related, gap-aware questions with rationale |
| 8 | `draft_outreach` | generation | `candidate_id`, `job_id` | honest outreach draft grounded in the match |
| 9 | `update_pipeline` | **write** | `candidate_id`, `job_id`, `to_stage`, `note?` | (on approval) moved stage + audit event |
| 10 | `add_candidate_note` | **write** | `candidate_id`, `body≤2000` | (on approval) stored note with source `agent` |

## Rules the registry enforces

- **Writes require approval — uniformly.** Both write tools become `PENDING` `ApprovalRequest`s; the orchestrator never executes them inline. Approval is the only path to mutation (ADR-0002).
- **Arguments are validated twice** — by the orchestrator before anything (including approval creation), and again by the executor. A malformed write never reaches the approval queue.
- **Outputs are validated** against declared output contracts before the agent sees them, so the model can only ground itself in well-formed data.
- **Errors are typed, not strings**: `entity_not_found`, `ambiguous_entity`, `validation_error`, `tool_failed`, … The agent must handle what actually happened.
- **No protected characteristics** appear in any input or output. Matching uses skills, experience, domain evidence only.

## Idempotency & replay

Approval keys are derived from `(conversation, tool, canonical args, attempt)`:

- proposing the same action again while one is **pending** → returns the same request (no duplicates);
- proposing it after it was **executed** → the executor refuses silently re-running it; the turn says so;
- proposing it after **rejection** → a *new* attempt is created so a human can change their mind — the rejection remains in history.

## The same surface everywhere

The REST API, the UI, the MCP server and the tests all execute through this one registry path (`app/tools/executor.py`). See `docs/MCP.md` for how MCP projects it safely.
