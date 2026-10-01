# ADR 0003 — MCP exposes reads and proposals, never silent writes

**Status:** accepted

## Context

The Model Context Protocol lets external clients (desktop assistants, editors) discover and call our capabilities. MCP clients cannot complete an in-app human approval, so exposing the write tools over MCP naively would break the approval guarantee that defines the product.

## Decision

The MCP server (`app/mcp_server.py`, stdio) exposes:

- **Reads:** `search_candidates`, `get_candidate`, `search_jobs`, `get_job`, `match_candidate`, `get_pipeline` — the same handlers the in-app agent uses, executed through the same validation/execution path.
- **One proposal tool:** `propose_pipeline_update` — creates a `PENDING` `ApprovalRequest` and mutates nothing. The human still decides in the app.

Write execution tools (`update_pipeline`, `add_candidate_note`) are **not** exposed over MCP. A client cannot execute a write through MCP at any point.

## Consequences

- The approval guarantee ("nothing changes without a human decision in the app") holds across every interface, including MCP.
- `tests/test_mcp_smoke.py` launches the real stdio server, calls read tools, asserts invalid arguments are rejected, and verifies that `propose_pipeline_update` creates a pending approval while the stage stays unchanged.
