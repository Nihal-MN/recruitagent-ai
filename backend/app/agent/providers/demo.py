"""The deterministic DEMO agent — a real orchestrator brain without an LLM.

This is *not* a chatbot script and not a mock of an LLM: it is a rule-based
planner that drives the SAME real tool registry the live provider drives, reads
its observations, and produces final answers that quote only tool results. It
exists so the entire product (approvals included) works with zero API keys —
and so behavioural evals can run hermetically. It is always labeled
``deterministic demo agent`` in the UI and health page.

Injection stance: the planner NEVER interprets tool output as instructions —
only the user's message selects an intent; observations are rendered as data.
"""

from __future__ import annotations

import re

from app.agent.providers.base import AgentState, Observation, StepDecision, ToolCall
from app.services.skills import canonicalize

_ROLE_RE = re.compile(
    r"(?:for|about)\s+(?:the\s+)?(.+?)(?:\s+(?:role|position|opening))?[?.!]*$",
    re.IGNORECASE,
)
_NAME_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b")
_STAGE_RE = re.compile(
    r"\b(new|screening|shortlisted|interview|offer|hired|rejected)\b", re.IGNORECASE
)
_QUOTED_RE = re.compile(r"[\"“”']([^\"“”']{3,300})[\"“”']")
_STAGE_ORDER = ("NEW", "SCREENING", "SHORTLISTED", "INTERVIEW", "OFFER", "HIRED", "REJECTED")


def _strip_md(text: str) -> str:
    return text.strip().strip(". \t").rstrip("\n")


class DemoProvider:
    name = "demo"

    # ── step planning ───────────────────────────────────────────────────────

    def next_step(self, state: AgentState) -> StepDecision:
        msg = state.user_message.strip()
        low = msg.lower()
        obs = state.observations

        # Recover from error observations: explain what happened, groundedly.
        last = obs[-1] if obs else None
        if last is not None and not last.ok:
            return StepDecision(final_text=self._explain_error(last))

        # ---- staged flows -------------------------------------------------
        if len(obs) == 1 and obs[0].tool == "search_jobs" and obs[0].ok:
            jobs = (obs[0].data or {}).get("jobs") or []
            if jobs:
                return StepDecision(
                    tool_call=ToolCall("search_candidates", {"job_id": jobs[0]["id"], "limit": 8})
                )
            return StepDecision(final_text=self._no_job_found(msg))

        if len(obs) == 2 and obs[0].tool == "search_jobs" and obs[1].tool == "search_candidates":
            return StepDecision(final_text=self._find_summary(obs))

        if len(obs) == 1 and obs[0].tool == "get_candidate" and obs[0].ok:
            if self._wants_match(low):
                candidate = (obs[0].data or {}).get("id")
                job_id = self._context_job_id(state)
                if candidate and job_id:
                    return StepDecision(
                        tool_call=ToolCall(
                            "match_candidate", {"candidate_id": candidate, "job_id": job_id}
                        )
                    )
                return StepDecision(final_text=self._need_job_context())
            if self._wants_screening(low):
                candidate = (obs[0].data or {}).get("id")
                job_id = self._context_job_id(state)
                if candidate and job_id:
                    return StepDecision(
                        tool_call=ToolCall(
                            "generate_screening_questions",
                            {"candidate_id": candidate, "job_id": job_id},
                        )
                    )
                return StepDecision(final_text=self._need_job_context())
            return StepDecision(final_text=self._candidate_profile_summary(obs[0]))

        if len(obs) == 1 and obs[0].tool == "match_candidate" and obs[0].ok:
            if self._wants_screening(low):
                data = obs[0].data or {}
                return StepDecision(
                    tool_call=ToolCall(
                        "generate_screening_questions",
                        {"candidate_id": data.get("candidate_id"), "job_id": data.get("job_id")},
                    )
                )
            if self._wants_outreach(low):
                data = obs[0].data or {}
                return StepDecision(
                    tool_call=ToolCall(
                        "draft_outreach",
                        {"candidate_id": data.get("candidate_id"), "job_id": data.get("job_id")},
                    )
                )
            return StepDecision(final_text=self._match_explanation(obs[0]))

        # Two-step flows that started with a candidate lookup (get_candidate → X).
        if len(obs) == 2 and obs[0].tool == "get_candidate" and obs[1].ok:
            if obs[1].tool == "match_candidate":
                return StepDecision(final_text=self._match_explanation(obs[1]))
            if obs[1].tool == "generate_screening_questions":
                return StepDecision(final_text=self._screening_answer(obs[1]))
            if obs[1].tool == "draft_outreach":
                return StepDecision(final_text=self._outreach_answer(obs[1]))
            if obs[1].tool in ("update_pipeline", "add_candidate_note"):
                return StepDecision(final_text=self._approval_answer(obs[1]))

        if len(obs) == 1 and obs[0].tool == "generate_screening_questions" and obs[0].ok:
            return StepDecision(final_text=self._screening_answer(obs[0]))

        if len(obs) == 1 and obs[0].tool == "draft_outreach" and obs[0].ok:
            return StepDecision(final_text=self._outreach_answer(obs[0]))

        if len(obs) == 1 and obs[0].tool == "get_pipeline" and obs[0].ok:
            return StepDecision(final_text=self._pipeline_answer(obs[0]))

        if obs and obs[-1].tool in ("update_pipeline", "add_candidate_note"):
            return StepDecision(final_text=self._approval_answer(obs[-1]))

        # ---- first step: classify the request ------------------------------
        if len(obs) == 0:
            if self._is_greeting(low):
                return StepDecision(final_text=self._intro())
            if self._is_pipeline_question(low):
                return StepDecision(tool_call=ToolCall("get_pipeline", self._pipeline_args(state)))
            if self._wants_move(low):
                return self._propose_move(state)
            if self._wants_note(low):
                return self._propose_note(state)
            if self._wants_screening(low) or self._wants_outreach(low) or self._wants_match(low):
                return self._resolve_subject_first(state)
            if self._wants_find(low):
                role = self._extract_role(msg)
                return StepDecision(
                    tool_call=ToolCall("search_jobs", {"query": role or msg[:80], "limit": 5})
                )
            if self._wants_skill_search(low):
                skill = self._extract_skill(low)
                return StepDecision(
                    tool_call=ToolCall("search_candidates", {"skill": skill, "limit": 10})
                )
            name = self._extract_name(msg)
            if name:
                return StepDecision(tool_call=ToolCall("get_candidate", {"identifier": name}))
            candidates = self._extract_candidate_word(low)
            if candidates:
                return StepDecision(
                    tool_call=ToolCall("search_candidates", {"query": candidates, "limit": 10})
                )
            return StepDecision(final_text=self._unknown_request())

        # Fallback: never loop forever — close out grounded on what we have.
        return StepDecision(final_text=self._fallback_final(state))

    # ── intent helpers ───────────────────────────────────────────────────────

    def _is_greeting(self, low: str) -> bool:
        return bool(re.match(r"^\s*(hi|hello|hey|good (morning|afternoon|evening))\b", low))

    def _wants_find(self, low: str) -> bool:
        return bool(
            re.search(r"\b(find|search|show|who|source)\b", low)
            and re.search(r"\b(candidates?|people|profiles?)\b", low)
        ) or bool(re.search(r"\bfind candidates? for\b", low))

    def _wants_match(self, low: str) -> bool:
        return (
            bool(re.search(r"\bwhy\b|\bmatch\b|\bexplain\b|\bfit\b", low))
            and "screening" not in low
        )

    def _wants_screening(self, low: str) -> bool:
        return "screening" in low or "interview questions" in low or "questions" in low

    def _wants_outreach(self, low: str) -> bool:
        return bool(re.search(r"\boutreach\b|\bdraft\b|\bemail\b|\bmessage\b", low))

    def _wants_note(self, low: str) -> bool:
        return "note" in low

    def _wants_move(self, low: str) -> bool:
        return bool(re.search(r"\bmove\b|\badvance\b|\bsend\b.*\bto\b", low))

    def _is_pipeline_question(self, low: str) -> bool:
        return "pipeline" in low or "board" in low

    def _wants_skill_search(self, low: str) -> bool:
        return bool(re.search(r"\b(with|who know|knows)\b", low)) and "candidate" in low

    def _extract_role(self, msg: str) -> str | None:
        m = _ROLE_RE.search(msg)
        if not m:
            return None
        role = _strip_md(m.group(1))
        role = re.sub(r"^(the|a|an)\s+", "", role, flags=re.IGNORECASE)
        return role[:120] or None

    def _extract_name(self, msg: str) -> str | None:
        # Triggered single-word names: "show me Alex", "open Layla", "profile of Chen".
        trigger = re.search(
            r"\b(?:show(?:\s+me)?|get|open|view|profile(?:\s+of)?|about|find)\s+"
            r"(?:the\s+)?(?:candidate\s+)?([A-Z][a-z]{2,})\b",
            msg,
        )
        if trigger:
            return trigger.group(1)
        names = _NAME_RE.findall(msg)
        stop = {"The", "This", "That", "For", "Find", "Show", "Move", "Add", "Please", "Why", "And"}
        for name in names:
            first = name.split()[0]
            if first not in stop:
                return name
        return None

    def _extract_skill(self, low: str) -> str | None:
        m = re.search(
            r"(?:with|who knows?|know)\s+(?:experience\s+in\s+)?([a-z0-9+#./ ]{2,40})", low
        )
        if not m:
            return None
        return canonicalize(m.group(1).strip())

    def _extract_candidate_word(self, low: str) -> str | None:
        m = re.search(r"candidates?\s+(?:named|called)\s+([a-z ]{2,60})", low)
        return m.group(1).strip() if m else None

    def _extract_stage(self, msg: str) -> str | None:
        m = _STAGE_RE.search(msg)
        return m.group(1).upper() if m else None

    def _extract_note_body(self, msg: str) -> str | None:
        quoted = _QUOTED_RE.search(msg)
        if quoted:
            return quoted.group(1).strip()
        m = re.search(r"(?:note|saying|that)\s*[:\-]\s*(.+)$", msg, re.IGNORECASE)
        if m:
            return _strip_md(m.group(1))
        return None

    # ── grounded context from prior turns (no model memory needed) ──────────

    def _all_observations(self, state: AgentState) -> list[Observation]:
        return [*state.prior_observations, *state.observations]

    def _context_job_id(self, state: AgentState) -> int | None:
        for obs in reversed(self._all_observations(state)):
            for key in ("job_id",):
                if obs.args.get(key):
                    return int(obs.args[key])
                if obs.meta.get(key):
                    return int(obs.meta[key])
                data = obs.data or {}
                if data.get(key):
                    return int(data[key])
        return None

    def _context_candidate_id(self, state: AgentState) -> int | None:
        for obs in reversed(self._all_observations(state)):
            if obs.args.get("candidate_id"):
                return int(obs.args["candidate_id"])
            if obs.meta.get("candidate_id"):
                return int(obs.meta["candidate_id"])
            if obs.meta.get("top_candidate_id"):
                return int(obs.meta["top_candidate_id"])
            data = obs.data or {}
            if data.get("candidate_id"):
                return int(data["candidate_id"])
            if data.get("id") and obs.tool == "get_candidate":
                return int(data["id"])
        return None

    def _resolve_subject_first(self, state: AgentState) -> StepDecision:
        """Screening/match/outreach: make sure we know WHO, grounded via tools."""
        name = self._extract_name(state.user_message)
        candidate_id = self._context_candidate_id(state)
        if name:
            return StepDecision(tool_call=ToolCall("get_candidate", {"identifier": name}))
        if candidate_id:
            return StepDecision(
                tool_call=ToolCall("get_candidate", {"identifier": str(candidate_id)})
            )
        return StepDecision(
            final_text=(
                "I can do that — which candidate should I use? Name one (e.g. by full name) "
                "or first run a search like *find candidates for the Senior Backend Engineer* role."
            )
        )

    def _propose_move(self, state: AgentState) -> StepDecision:
        stage = self._extract_stage(state.user_message)
        if stage is None:
            return StepDecision(
                final_text="Which stage should I move them to? One of: "
                + ", ".join(_STAGE_ORDER)
                + "."
            )
        candidate_id = self._context_candidate_id(state)
        job_id = self._context_job_id(state)
        name = self._extract_name(state.user_message)
        if name and candidate_id is None:
            return StepDecision(tool_call=ToolCall("get_candidate", {"identifier": name}))
        if candidate_id is None or job_id is None:
            return StepDecision(
                final_text="I need context first — tell me the candidate and job "
                "(or search like *find candidates for the Senior Backend Engineer role*)."
            )
        return StepDecision(
            tool_call=ToolCall(
                "update_pipeline",
                {"candidate_id": candidate_id, "job_id": job_id, "to_stage": stage},
            )
        )

    def _propose_note(self, state: AgentState) -> StepDecision:
        body = self._extract_note_body(state.user_message)
        candidate_id = self._context_candidate_id(state)
        name = self._extract_name(state.user_message)
        if name and candidate_id is None:
            return StepDecision(tool_call=ToolCall("get_candidate", {"identifier": name}))
        if candidate_id is None:
            return StepDecision(
                final_text="Which candidate is the note for? Name one or search first."
            )
        if body is None:
            return StepDecision(
                final_text='What should the note say? Example: add a note "Strong systems depth."'
            )
        return StepDecision(
            tool_call=ToolCall("add_candidate_note", {"candidate_id": candidate_id, "body": body})
        )

    def _pipeline_args(self, state: AgentState) -> dict:
        job_id = self._context_job_id(state)
        return {"job_id": job_id} if job_id else {}

    # ── grounded final answers (built ONLY from observations) ───────────────

    def _intro(self) -> str:
        return (
            "Hi! I'm your recruiting operations agent. I work through explicit tools — "
            "I can:\n"
            "• find candidates for a role (try: *find candidates for the "
            "Senior Backend Engineer* role)\n"
            "• explain why someone matches (*why does this candidate match?*)\n"
            "• generate screening questions and outreach drafts\n"
            "• propose pipeline moves and notes — **always with your approval "
            "before anything changes**.\n\n"
            "Nothing I do writes to the database without you approving it first."
        )

    def _no_job_found(self, msg: str) -> str:
        role = self._extract_role(msg) or msg[:60]
        return (
            f"I couldn't find a job matching *{role}* in the system, so I won't guess — "
            "no candidates were invented. Check the Jobs page for the exact open roles, "
            "or give me the full title."
        )

    def _find_summary(self, obs: list[Observation]) -> str:
        jobs = (obs[0].data or {}).get("jobs") or []
        candidates = (obs[1].data or {}).get("candidates") or []
        job = jobs[0]
        if not candidates:
            return (
                f"No candidates matched for *{job['title']}* — nothing invented. "
                "Try a broader search or check the Candidates page."
            )
        lines = [f"Here are candidates for **{job['title']}** (ranked by explainable match):", ""]
        for rank, c in enumerate(candidates[:6], start=1):
            score = c.get("match_score")
            score_text = f" — {score}/100" if score is not None else ""
            lines.append(f"{rank}. **{c['full_name']}**{score_text} · {c.get('headline') or '—'}")
        lines.append("")
        lines.append(
            "I can explain any of these (*why does this candidate match?*), draft screening "
            "questions, or propose a pipeline move (you'll approve it first)."
        )
        return "\n".join(lines)

    def _match_explanation(self, obs: Observation) -> str:
        d = obs.data or {}
        met = d.get("coverage", {}).get("must_have_met", 0)
        partial = d.get("coverage", {}).get("must_have_partial", 0)
        missing = d.get("coverage", {}).get("must_have_missing", 0)
        lines = [
            f"**{d.get('candidate_name')}** vs **{d.get('job_title')}**: "
            f"**{d.get('score')}/100** — {met} must-have met · {partial} partial · "
            f"{missing} missing.",
            f"Formula: `{d.get('formula')}`",
            "",
        ]
        for r in d.get("requirements") or []:
            if r["kind"] != "must_have":
                continue
            evidence = (r.get("evidence") or [{}])[0].get("snippet")
            icon = {"met": "✅", "partial": "🟡", "missing": "❌", "unknown": "❔"}.get(
                r["status"], "•"
            )
            line = f"{icon} {r['label'][:80]} — {r['reason'][:110]}"
            if evidence and r["status"] in ("met", "partial"):
                line += f"\n   ↳ “{evidence[:140]}”"
            lines.append(line)
        lines.append("")
        lines.append("Ranking is deterministic — the same inputs always produce the same result.")
        return "\n".join(lines)

    def _screening_answer(self, obs: Observation) -> str:
        d = obs.data or {}
        lines = [
            f"Screening questions for **{d.get('candidate_name')}** · **{d.get('job_title')}** "
            f"(grounded in the match; generated by {d.get('generated_by')}):",
            "",
        ]
        for i, q in enumerate(d.get("questions") or [], start=1):
            lines.append(f"{i}. {q['question']}")
            lines.append(f"   _Why: {q['rationale']}_")
        lines.append("")
        lines.append(
            "All questions are job-related — none touch protected or personal circumstances."
        )
        return "\n".join(lines)

    def _outreach_answer(self, obs: Observation) -> str:
        d = obs.data or {}
        return (
            f"Outreach draft for **{d.get('candidate_name')}** · **{d.get('job_title')}**\n\n"
            f"**Subject:** {d.get('subject')}\n\n{d.get('body')}\n\n"
            "_Draft only — nothing was sent. Copy it or ask me to adjust the tone._"
        )

    def _pipeline_answer(self, obs: Observation) -> str:
        d = obs.data or {}
        columns = d.get("columns") or {}
        lines = [f"Pipeline board — {d.get('total', 0)} application(s):", ""]
        for stage in _STAGE_ORDER:
            items = columns.get(stage) or []
            if items:
                names = ", ".join(i["candidate_name"] for i in items)
                lines.append(f"• **{stage}**: {names}")
        lines.append("")
        lines.append("Ask me to move someone and I'll create an approval request first.")
        return "\n".join(lines)

    def _candidate_profile_summary(self, obs: Observation) -> str:
        d = obs.data or {}
        skills = ", ".join(s["normalized_name"] for s in (d.get("skills") or [])[:10])
        apps = d.get("applications") or []
        app_lines = [f"• {a['job_title']} — {a['stage']}" for a in apps] or [
            "• not in any pipeline yet"
        ]
        return (
            f"**{d.get('full_name')}** — {d.get('headline') or ''}\n"
            f"{d.get('location') or ''} · {d.get('years_experience') or '?'} years of "
            "experience\n\n"
            f"Skills: {skills}.\n\nIn pipeline:\n" + "\n".join(app_lines)
        )

    def _approval_answer(self, obs: Observation) -> str:
        if obs.error_code:  # e.g. duplicate executed action — from orchestrator note
            return obs.summary
        return (
            "That's a consequential write, so I've created an **approval request** instead of "
            "executing it:\n\n"
            f"→ {obs.summary}\n\n"
            "Nothing has changed yet. Open **Approvals** to approve or reject it — I execute "
            "only after you approve, exactly once."
        )

    def _explain_error(self, obs: Observation) -> str:
        mapping = {
            "entity_not_found": f"I couldn't find that: {obs.summary} Nothing was invented.",
            "ambiguous_entity": f"That's ambiguous: {obs.summary}",
            "validation_error": f"I couldn't run that safely: {obs.summary}",
            "max_steps_exceeded": "I hit my execution limit for one request. Ask me to continue.",
            "policy_blocked": f"Blocked by policy: {obs.summary}",
            "approval_rejected": f"Understood — {obs.summary}",
        }
        return mapping.get(
            obs.error_code or "", f"That action failed safely ({obs.error_code}): {obs.summary}"
        )

    def _need_job_context(self) -> str:
        return (
            "I need a job context first — tell me the role (or start with a search like "
            "*find candidates for the Senior Backend Engineer* role)."
        )

    def _unknown_request(self) -> str:
        return (
            "I can help with: finding candidates for a role, explaining a match, screening "
            "questions, outreach drafts, recruiter notes and pipeline moves. "
            "Try: *find candidates for the Senior Backend Engineer role*."
        )

    def _fallback_final(self, state: AgentState) -> str:
        if state.observations and state.observations[-1].tool == "search_candidates":
            obs = state.observations[-1]
            candidates = (obs.data or {}).get("candidates") or []
            if not candidates:
                return "No candidates matched that search — nothing invented."
            lines = ["Matches from the search:", ""]
            for c in candidates[:8]:
                lines.append(f"• **{c['full_name']}** · {c.get('headline') or '—'}")
            return "\n".join(lines)
        return (
            "I've gathered what I can for this request. Tell me the next step — explain a "
            "match, generate screening questions, or propose a pipeline move."
        )

    # ── generation methods (used by the generation service in demo mode) ────

    def generate_screening_questions(self, match, count: int) -> list[dict]:
        from app.services.generation import _demo_questions

        return _demo_questions(match, count)

    def draft_outreach(self, match) -> dict:
        from app.services.generation import _demo_outreach

        draft = _demo_outreach(match)
        return {"subject": draft["subject"], "body": draft["body"]}
