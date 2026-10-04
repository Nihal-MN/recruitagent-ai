## What & why

<!-- One paragraph: what changed and the reason it should exist. Link the issue if there is one: Fixes #__ -->

## The checklist (please keep all boxes true)

- [ ] `make test` and `make test-frontend` pass locally (or explain why they can't run).
- [ ] `make lint` is clean.
- [ ] **The one rule holds:** no writes execute without a human approval. (If this PR adds a tool, its `kind`/`requires_approval` classification is correct and documented in `docs/TOOLS.md`.)
- [ ] If agent behavior changed, an eval scenario was added/updated in `backend/tests/evals/` — or I explain why not in this description.
- [ ] Docs match the code (README / docs/\* / CHANGELOG as applicable).
- [ ] No secrets, no real candidate data, no personal emails in commits (synthetic examples only).

## Screenshots / trace output (if UI- or agent-facing)

<!-- Optional but appreciated: before/after screenshots, or the Tool Trace rows for a changed flow. -->
