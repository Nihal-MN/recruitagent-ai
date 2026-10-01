# MCP server

RecruitAgent ships an MCP server so external clients (Claude Desktop, editors, agent frameworks) can use its read capabilities and propose actions — without ever bypassing the approval gate.

## Run it

```bash
make mcp
# or: cd backend && uv run python -m app.mcp_server    (stdio transport)
```

Client configuration (Claude Desktop style):

```json
{
  "mcpServers": {
    "recruitagent": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/recruitagent-ai/backend", "python", "-m", "app.mcp_server"],
      "env": { "DATABASE_URL": "sqlite:///./recruitagent-dev.db" }
    }
  }
}
```

(Use the same `DATABASE_URL` as the app so both see the same data.)

## Tools exposed

**Reads** (identical handlers to the in-app agent, same validation):
`search_candidates` · `get_candidate` · `search_jobs` · `get_job` · `match_candidate` · `get_pipeline`

**Proposal-only write:**
`propose_pipeline_update(candidate_id, job_id, to_stage, note?)` — creates a **PENDING approval** and mutates nothing. The proposal appears in the app's Approvals page; the human decides there. An MCP client cannot execute it, now or later.

Write *execution* tools (`update_pipeline`, `add_candidate_note`) are deliberately **not exposed**. Rationale in [docs/adr/0003](adr/0003-mcp-read-plus-proposals.md).

## Guarantees

- Every call goes through the same executor: strict Pydantic validation, typed errors, sanitized traces.
- Invalid arguments return MCP tool errors (e.g. `limit=999` is rejected by the contract).
- No mutation can originate from MCP — the worst an MCP client can do is queue a proposal for a human to reject.

## Smoke test

`backend/tests/test_mcp_smoke.py` launches the real stdio server as a subprocess against a file-backed SQLite database and, via the official MCP client:

1. lists tools and asserts the expected set;
2. calls `search_candidates` recursively and checks results;
3. calls `match_candidate` and asserts the score is present;
4. asserts over-limit arguments come back as tool errors;
5. calls `propose_pipeline_update` and verifies **in the database** that an approval exists as PENDING and the application stage is unchanged.
