# Contributing

Thanks for looking! This is a small, deliberately comprehensible project — contributions that keep it that way are welcome.

## Development setup

```bash
# Backend (Python 3.12+, uv)
cd backend
uv sync
uv run alembic upgrade head        # SQLite dev db by default
uv run python -m app.seed
uv run uvicorn app.main:app --reload

# Frontend (Node 22+)
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev   # binds :3200
```

Or the whole stack in Docker: `make up && make seed`.

## Before you open a PR

```bash
make test    && make test-frontend && make lint
```

- Backend: `ruff` clean, `pytest` green (73 tests incl. evals + MCP smoke).
- Frontend: `eslint`, `tsc --noEmit`, `vitest`.
- CI runs all of the above plus a Docker build on every push.

## Principles to preserve

1. **Providers plan; the platform enforces.** Never let a provider (or an MCP client) execute writes, skip validation, or bypass bounds.
2. **Writes require approval.** New tools must declare `kind` honestly; write tools go through the approval path.
3. **Ground everything.** Answers and match verdicts must trace to tool results / stored evidence. No invented entities — add an eval if you touch this area.
4. **Untrusted content stays data.** Resume/JD/note text is never interpreted as instructions.
5. **No protected characteristics** in schemas, matching or answers — `tests/test_matching.py` guards the schema.
6. **Small and auditable.** Prefer clear code over frameworks; this loop is meant to be read in one sitting.

## Adding a tool

1. Add its input/output contracts in `app/tools/contracts.py`.
2. Implement the handler in `app/tools/builtin.py` and register it with the right `kind`/`requires_approval`.
3. Add tests (contract + behavior) and, if user-visible, an eval scenario.
4. Update `docs/TOOLS.md`.

## Commit style

Conventional-ish prefixes (`feat:`, `fix:`, `docs:`, `test:`, `chore:`) and a sentence that says *why*. Small commits are appreciated.
