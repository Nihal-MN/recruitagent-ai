# GitHub for owner — RecruitAgent AI maintainer manual

Everything you need to run, show and maintain this repo. Skim it once; keep it for the day someone opens an issue.

## Your repo at a glance

| Thing | Value |
|---|---|
| Repo | `https://github.com/Nihal-MN/recruitagent-ai` (public, MIT) |
| Default branch | `main` — protected by CI on every push |
| Release | `v0.1.0` (tag) |
| Discussions | Enabled — announcements live there |
| The pitch | *"The model proposes, humans decide."* |

## Day-one tasks (10 minutes, your clicks)

1. **Upload the social preview** (the card people see when the link is shared):
   - File: `docs/assets/social-preview.png` (also copied to your Desktop as `RecruitAgent-social-preview_UPLOAD-THIS-1280x640.png`).
   - GitHub → repo → **Settings → General → Social preview → Edit → Upload** that PNG. Pick the **PNG** (SVG is rejected silently).
2. **Pin the announcement**: open the discussion in **Discussions → Announcements** → right side → **Pin discussion**.
3. **Post on LinkedIn** when ready — paste-ready text in `PORTFOLIO_DRAFT.md` (short version recommended).

## How this repo is run (so you can answer anything)

- **CI** (`.github/workflows/ci.yml`): backend lint+tests (74, hermetic), frontend lint/typecheck/tests/build, Docker build. **CodeQL** also runs on `main`.
- **Dependabot** (`.github/dependabot.yml`): weekly updates for pip, npm, actions, docker. When a PR appears: let CI go green, read the changelog link, merge. For major bumps that fight CI, it's fine to close with a comment "upstream-blocked" and revisit.
- **Security**: secret scanning + push protection + Dependabot alerts are enabled in Settings → Security. Trust them; when something lights up, read it before reacting.
- **Discussions**: announcements category. Use it for release notes; keep Issues for actionable bugs.
- **Labels**: default set + `backend`, `frontend`, `agent-core`, `tools`, `approvals`, `mcp`, `security`, `evals`, `database`, `ci`, `dx`, `roadmap`.
- **Issues**: the open backlog mirrors `ROADMAP.md` — they're honest "next steps", not promises with dates.

## Local operations cheat-sheet

```bash
make up        # build + start (db, api, web)     make down   # stop
make seed      # reseed demo data (20 candidates) make logs   # tail logs
make test      # backend incl. evals + MCP smoke  make lint   # ruff + eslint + tsc
make mcp       # run the MCP server (stdio)
```

Ports: web `3000` · api `8000` · db `5432` (change in `.env` — see `.env.example`).

## If someone reports "I think there's a bug"

1. Reproduce locally: `make up && make seed`, try their steps.
2. Check the **Tool Trace** page and **Activity** — most "the agent did something weird" cases are visible there (and usually it's a *proposal*, not an action).
3. If it's real: open an issue with the label, add it to your own backlog, fix with a test. The eval suite (`backend/tests/evals/`) is where behavioral fixes get locked in — add one.

## The one rule to never break

**Writes must always require approval.** If a future PR (yours or someone else's) adds a write tool that executes directly, that PR is wrong by definition — see `docs/adr/0002-approvals-and-idempotency.md`. Same for MCP: reads + proposals only (ADR-0003).

## Sharing the repo

- LinkedIn/X copy: `PORTFOLIO_DRAFT.md`.
- For code reviewers: point them at `docs/CHATGPT_REVIEW_HANDOFF.md` (it lists claims → files → adversarial checklist).
- For interviews: `docs/TALENT_ENGINEER_INTERVIEW_GUIDE.md`.
