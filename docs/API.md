# API

Base URL: `http://localhost:8000/api/v1` (configurable ports; OpenAPI docs at `/docs`).

All errors use one envelope:

```json
{ "error": { "code": "entity_not_found", "message": "No candidate matches 'Nobody'.", "detail": null } }
```

Codes map to HTTP statuses: `entity_not_found`→404, `validation_error`→422, `ambiguous_entity`/`approval_required`/`approval_rejected`/`policy_blocked`→409, `provider_unavailable`→503, `tool_failed`→500, `max_steps_exceeded`→429.

## Agent

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/conversations` | list conversations |
| `POST` | `/conversations` | create (`{title?}`) |
| `GET` | `/conversations/{id}` | messages + tool executions + approvals |
| `POST` | `/conversations/{id}/messages` | send a user message (`{content}`); runs one agent turn; returns `final_text`, `stopped_reason`, ids of created messages/executions/approvals |

## Approvals (the human gate)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/approvals?status=` | list (newest first) |
| `POST` | `/approvals/{id}/approve` | execute the proposal exactly once (`{decided_by?}`) |
| `POST` | `/approvals/{id}/reject` | reject — zero mutation |

Approving an already-executed request returns the stored result without re-executing; a decided request cannot be re-decided.

## Transparency

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/tool-executions?conversation_id=&limit=` | the tool trace (sanitized args, status, duration, approval link) |
| `GET` | `/activity?limit=` | append-only audit: proposals, decisions, executions, moves, notes |

## Directory

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/candidates?query=&skill=&limit=&offset=` | list (`X-Total-Count` header) |
| `GET` | `/candidates/{id}` | profile + evidence-bearing skills + applications + notes |
| `GET` | `/jobs` · `/jobs/{id}` | jobs + requirements |
| `GET` | `/pipeline?job_id=` | board grouped by stage |

## System

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | status, DB dialect + counts, AI mode (provider, model, key-configured) — never secrets |

## Notes

- No authentication by design (local demo). See `SECURITY.md` before exposing the port.
- The agent's write path is ONLY through approvals; there are no direct mutation endpoints for stages or notes.
