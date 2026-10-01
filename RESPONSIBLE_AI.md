# Responsible AI

Recruiting is a domain where AI mistakes have human consequences. This page states plainly what RecruitAgent does, what it refuses to do, and where the limits are.

## What this project deliberately does NOT do

- **No automated hiring decisions.** The agent never decides to hire, reject or rank humans as a verdict; it assembles evidence for a human recruiter. There is no tool that can set anyone to HIRED as a decision — only a stage change that a human must approve, and stages are operational state, not decisions.
- **No protected characteristics.** The schema stores none (enforced by a test), matching uses none, and the agent refuses requests that ask for them ("show me female candidates", "only young people") with an explanation, executing no tools.
- **No hidden automation.** Writes cannot execute without a recorded approval. There is no bypass, including over MCP (proposal-only).
- **No reasoning store.** The tool trace records operational events (name, args summary, status, duration) — never chain-of-thought, and the UI says so.

## What it does, and how it stays honest

- **Evidence-first matching.** Every requirement verdict quotes its source line from the stored resume text; a test asserts traceability for the seeded dataset. Insufficient data returns "unknown" — not a guess.
- **Grounded answering.** The demo provider builds answers from tool outputs only; the OpenAI provider is instructed to do the same and to report tool failures instead of inventing. Evals assert no invented entities.
- **Untrusted content posture.** Resume/JD/note text is data; prompt-injection attempts cannot trigger writes or change policy (evals 17–19).
- **Transparency surfaces.** Tool trace, approval history and an append-only activity log are first-class pages, not debug extras.

## Known limitations (honest list)

- Matching is a deliberately simple, explainable heuristic (skills, years, domain, location) — not a validated psychometric or sourcing model.
- The demo agent is deterministic and narrow; the OpenAI path is your own key. Neither is a fairness-certified system.
- No fairness audit across demographics is possible *because no demographic data is stored* — this is a deliberate trade-off: absence of bad data beats post-hoc correction, but it also means parity testing must happen at the process level, outside this system.
- Single-node demo: no multi-tenant isolation, no auth, no rate limiting. See SECURITY.md.

## If you deploy this for real

Treat it as a starting point: add authentication and per-tenant scoping first, keep every action approval-gated, retain the audit trail, and involve legal/compliance for your jurisdiction before processing real candidate data.
