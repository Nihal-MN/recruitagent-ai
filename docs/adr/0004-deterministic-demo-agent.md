# ADR 0004 — A deterministic demo agent instead of "demo mode" theater

**Status:** accepted

## Context

Keyless demos usually fake the interesting parts: canned responses, scripted tool traces, or a degraded "demo mode" that bypasses the real pipeline. That makes the demo dishonest — a reviewer cannot tell what is actually built — and it makes 90% of the codebase untestable without an API key.

## Decision

Ship a real, deterministic provider (`app/agent/providers/demo.py`) that:

- plans against conversation state and prior tool observations, exactly like an LLM would (intent → tool choice → observation → next step → final);
- drives the **same** registry, executor, approvals, traces and bounds;
- grounds every sentence of its final answers in actual tool results (scores, names, stages, evidence quotes);
- refuses protected-characteristic requests, invents nothing, and requires approvals for writes — because policy lives in the loop, not the prompt.

The UI labels it explicitly ("DEMO AGENT · no API key") and `docs/EVALUATIONS.md` runs the behavioral suite against it. The OpenAI provider is selected automatically when a key exists; when it is, generation becomes model-driven but every guarantee stays identical.

## Consequences

- `docker compose up` gives a fully working, honest product in minutes — the headline claim of the README.
- The eval suite is hermetic and fast (no network), so it runs in CI on every push.
- We maintain one extra planning implementation. Accepted: it doubles as executable documentation of expected agent behavior.
