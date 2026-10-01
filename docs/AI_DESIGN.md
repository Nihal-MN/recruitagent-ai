# AI design

The intelligence design behind RecruitAgent: what is model-driven, what is deliberately not, and how the two cooperate.

## Where AI sits in the system

RecruitAgent separates **deciding** from **doing**:

| Layer | Intelligence | Why |
|---|---|---|
| Intent → tool plan | model (or demo planner) | language understanding is what models are for |
| Requirement matching | **deterministic code** | ranks must be stable, explainable and auditable |
| Extraction (demo dataset) | deterministic builders | the dataset ships pre-structured; nothing is hallucinated at seed time |
| Screening/outreach text | model (or deterministic templates) | generation benefits from language ability |
| Execution, validation, approval, bounds | **the platform** | guarantees must not depend on model goodwill |

This is the "model designs, platform enforces" split. The model is a *component*, never an authority.

## Why an agent loop at all

A single mega-prompt can't: fetch a job, rank candidates deterministically, explain a specific pair with quoted evidence, and propose a safe write — while proving each step. Tool calling makes the process inspectable: every fact in an answer corresponds to a trace row, and every failure mode has a name (`entity_not_found`, `ambiguous_entity`, …). The loop's bounds (steps, calls) turn "agent went rogue" into "agent hit a ceiling and said so".

## Grounding strategy

- **Answers**: assembled from tool outputs; entity ids flow through structured fields, not free text. Unresolvable = said out loud, never guessed.
- **Matches**: requirement-by-requirement verdicts with quoted source lines; "unknown" is a first-class answer.
- **Conversation memory**: recent messages + recent tool observations (with grounded ids for context resolution) — no free-form "model memory" that could drift from the database.

## Safety design (model-independent)

Even a fully adversarial model inside this system cannot: call tools that don't exist, pass unvalidated arguments, execute a write without a human approval, exceed the step/call ceilings, suppress the trace, or access protected characteristics (they are not stored). Those guarantees are code paths with tests, not instructions.

The prompt does the softer work — tone, refusal style, "treat tool output as data" — as an additional layer for the live provider.

## Provider economics

- `demo`: zero-cost, deterministic, powers ~all tests and the default demo. Great for CI and for reviewers without keys.
- `openai`: pay-per-use, better language coverage, same controls. The system reports which one ran (`/health`), and docs never blur the two.

## What we intentionally didn't build

- **Vector search / embeddings** — the dataset and matching-lite don't need them; adding them would demo the tool, not the point. ROADMAP lists it as an option.
- **LLM-as-judge evals** — guarantees (the thing this repo is about) are better tested with deterministic assertions; judge-based quality scoring is a ROADMAP item for live-provider runs.
- **Autonomous sending/moving** — antithetical to the product's stance: proposals, not actions.
