# Roadmap

Where RecruitAgent can go next — roughly ordered by the distance from "portfolio demo" to "production posture". Nothing here is committed; issues and PRs welcome.

## v0.2 — Security posture

- [ ] Authentication (email magic-link or OAuth) + per-user scoping of conversations and approvals
- [ ] Rate limiting on agent turns and approvals
- [ ] Structured logging with request ids; optional OpenTelemetry traces

## v0.3 — Agent depth

- [ ] Streaming turn output (SSE) for tool-by-tool progress in the chat UI
- [ ] Conversation compaction/summarization so long threads keep grounded context
- [ ] Time-bounded approvals (auto-expire stale proposals)
- [ ] Richer generation providers (Anthropic, local models) behind the same provider protocol

## v0.4 — Recruiting depth

- [ ] Resume/JD file ingestion pipeline (PDF/DOCX) feeding the same extraction path
- [ ] Interview scheduling tool (calendar integration, approval-gated)
- [ ] Email sending via Gmail/Resend — always approval-gated, never auto-send
- [ ] Saved searches and daily digests delivered as proposals, not actions

## v0.5 — Evaluation depth

- [ ] LLM-as-judge scoring for live-provider runs (quality, not just guarantees)
- [ ] Scenario fuzzing for tool-argument robustness
- [ ] Latency/cost dashboards per tool and provider

## Explicit non-goals

- Automated hiring decisions, ranking humans as verdicts, or any use of protected characteristics.
- Autonomous sends/moves — this product's identity is that a human decides.
- Multi-tenant SaaS complexity in the OSS repo.
