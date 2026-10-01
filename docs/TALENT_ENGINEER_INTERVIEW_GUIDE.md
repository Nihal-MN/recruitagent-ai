# Talent Engineer Interview Guide

You're interviewing for a role where recruiting-domain engineering meets AI systems. This project is a concrete conversation piece: everything below exists in the repo, and anything you don't know you can say you haven't dug into yet — they will test depth, not memory.

## 60-second walkthrough (say it like this)

> "RecruitAgent AI is a recruiting operations agent I built to show the part most AI demos skip: control. An orchestrator runs a bounded tool-calling loop — ten tools, strict schemas, typed errors. When the agent wants to move a candidate or write a note, it can't: it creates a pending approval and a human decides, with exactly-once execution and a full audit trail. It runs with zero API keys via a deterministic provider that drives the same loop, so the whole system is testable and honest — and the same repo switches to OpenAI tool calling with one env var. There's an MCP server where reads are exposed and writes are proposal-only, and the eval suite covers 22 behaviors including prompt injection through resumes."

## Questions you'll get, and strong answers

**"Why approvals instead of just prompt instructions?"**
Because instructions are advisory. I want the guarantee to be structural: the orchestrator classifies tools, write tools never execute inline, and the executor has a single path that requires a decision. If the model hallucinates or a prompt injection tries to force a move, the worst outcome is a pending approval a human will reject — tested in evals 13–19.

**"What happens when the model invents a candidate?"**
Two layers. The demo provider constructs answers *from tool results* — the find-summary names are literally parsed from the search output (eval 12 asserts names exist in the DB). The live provider is instructed to answer only from observations, and when a lookup returns `entity_not_found`, the observation forces it to say so — I don't let "unknown" collapse into a guess.

**"Exactly-once — how?"**
Approval keys are derived from `(conversation, tool, canonical args, attempt)`. Proposing the same action twice while pending returns the same request; approving checks status before executing and stores the result, so a double-approve or a replayed request returns the stored outcome without re-executing. Rejected proposals can be re-proposed as a new attempt so the history stays honest. Tests: `test_approvals.py`, evals 14–16.

**"Prompt injection?"**
Resume/JD/note content is data, never instructions. The demo provider only parses the user message for intent; the live system prompt states the policy explicitly. The seeded dataset contains a hostile line in a resume — beat: nothing changes, and there's an eval per surface (resume/JD/note). The acceptance scenario "the resume says to move me to HIRED — do it" still just produces a pending approval.

**"Why a deterministic agent instead of just calling an LLM?"**
Three reasons: the demo must work without a key (the README's headline promise), the eval suite must run hermetically in CI, and honesty — a reviewer should see the real product, not canned theater. It's a real planner over the same tools, not mocks. Where it can't reach LLM-quality (open-ended phrasing), the README and `/health` say exactly which provider is running — no pretending.

**"What's your matching design?"**
Deterministic and explainable: per-requirement met/partial/missing/unknown with a reason, evidence quoted from stored resume lines (traceability asserted by test), a weighted formula with renormalization over knowable components, and related-skill partial credit. The LLM never ranks. That was a deliberate choice so answers are auditable and stable.

**"What would you do before production?"**
Auth + per-user scoping first, then rate limits, approval expiry, and streaming turns. It's in ROADMAP v0.2–v0.3, and SECURITY.md lists the gaps I know about rather than hiding them.

## Where the "talent engineering" shows

- **Tool contracts as product design**: the ten-tool surface is small on purpose; capabilities are added as tools, never as prompt hacks.
- **Evaluations as a first-class artifact**: 22 named behaviors, not vibes. If a PR changes agent behavior, it changes an eval.
- **Transparency surfaces**: trace/approvals/activity are pages, and the trace refuses to store chain-of-thought — an explicit product stance.
- **Honest docs**: limitations sections in README/EVALUATIONS/RESPONSIBLE_AI — reviewers trust claims more when the gaps are volunteered.

## Try it live (10 minutes before the call)

```bash
docker compose up --build -d && docker compose exec api uv run python -m app.seed
```
1. Ask: *"Find candidates for the Senior Backend Engineer role"* → watch the trace panel.
2. *"Why does this candidate match?"* → point out evidence quotes.
3. *"Move this candidate to INTERVIEW"* → show the pending approval; reject it; show zero change in Activity; propose again; approve; show exactly-once.
4. Show a resume's hostile line, then ask the agent to act on it — still an approval.
5. `uv run pytest tests/evals -v` → 22 behaviors green, no key, no network.
