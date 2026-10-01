# Security

## Intended use

RecruitAgent AI is a **local demo / portfolio system**. It ships with **no authentication** — by design, so reviewers can `docker compose up` and explore. `docker compose` publishes ports bound to your machine only by default; do not expose this stack to the internet, and never load real candidate data into it.

## What is protected

- **Write actions.** Every consequential write (pipeline move, candidate note) requires a human approval executed through the backend; approval executes exactly once. This holds for the agent loop, the REST API and MCP (proposal-only).
- **Prompt injection.** Resume/JD/note content is treated as untrusted data; injection attempts cannot trigger writes or alter policy (tested).
- **Secrets.** No secrets are committed or logged. `/health` reports configuration booleans, never values. If you add an OpenAI key, keep it in `.env` (git-ignored) or your runtime's secret store.
- **Input validation.** Tool arguments and API payloads are validated with strict Pydantic contracts on both entry paths.
- **Error surfaces.** Errors are typed codes with safe messages; internal traces are not returned to clients.

## Not protected (by design, documented)

- **No authN/authZ.** Anyone who can reach the port can use the API and decide approvals. This is the single biggest gap before any non-local use — it is item #1 on the production checklist in ROADMAP.md.
- **No rate limiting / quotas.**
- **No tenant isolation.** One dataset per deployment.
- **SQLite dev fallback** is for local development; Docker/Postgres is the supported deployment.

## Reporting

Found a vulnerability? Please open a private security advisory or email the maintainer rather than a public issue. Include reproduction steps; expect an acknowledgement within a few days. This is a personal open-source project — no bounty program, but genuine reports are fixed quickly and credited.

## Hardening checklist if you extend this

1. Add authentication + per-user scoping before exposing any port.
2. Keep approvals server-enforced and audit-logged; never add a "trusted agent" bypass.
3. Keep the write tools' require-approval classification — it is the product.
4. Run `uv run pytest` and the Docker build in CI before every deploy (already wired).
5. Pin and update dependencies (Dependabot config included).
