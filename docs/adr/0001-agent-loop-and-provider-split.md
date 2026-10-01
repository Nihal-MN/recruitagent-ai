# ADR 0001 — A bounded agent loop with a provider abstraction

**Status:** accepted

## Context

The product needs an agent that can call recruiting tools, but portfolio demos die twice: they either fake the "agent" with canned scripts, or they require an API key to do anything at all. We wanted one orchestrator whose behavior is real regardless of the model behind it.

## Decision

All agent turns run through a single bounded loop (`app/agent/orchestrator.py`):

```
user message → provider.next_step(state) → typed tool call
→ schema validation → authorization policy → execution
→ safe trace event → observation → … → grounded final answer
```

The loop is provider-agnostic. Two providers implement the same `Provider` protocol:

- `demo` — a deterministic rule-based planner that drives the **same** tool registry, approvals and traces. No API key, no network; used by the demo UI and the entire hermetic test/evals suite.
- `openai` — live tool calling (Responses API function tools) plus structured generation, selected when `OPENAI_API_KEY` is set (`AI_PROVIDER=auto`).

Providers decide; they can never execute. The orchestrator owns validation, policy, execution, tracing and bounds (max steps, max tool calls).

## Consequences

- Every behavior that matters (grounding, approvals, injection resistance, bounds) is tested without an LLM, deterministically.
- Swapping the model changes planning quality, not the security posture.
- The demo agent is code we own and can explain — not a mocked LLM.

## Alternatives considered

- **Direct SDK calls inside routes** — untestable, mixes policy with I/O, rejected.
- **LangChain-style graph frameworks** — heavy dependency for a small, auditable loop; rejected for this project's scale.
