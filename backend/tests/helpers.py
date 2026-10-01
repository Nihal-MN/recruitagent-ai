"""Shared test doubles + helpers."""

from __future__ import annotations

from app.agent.providers.base import StepDecision
from app.core.errors import AppError, ErrorCode


class ScriptedProvider:
    """Test double: replays a fixed decision queue (then a final answer).

    Accepts ``StepDecision`` objects directly, or bare ``ToolCall`` items
    (wrapped automatically).
    """

    name = "scripted"

    def __init__(self, decisions):
        self.decisions = list(decisions)

    def next_step(self, state):
        if not self.decisions:
            return StepDecision(final_text="script exhausted")
        decision = self.decisions.pop(0)
        if isinstance(decision, StepDecision):
            return decision
        return StepDecision(tool_call=decision)

    def generate_screening_questions(self, match, count):
        return []

    def draft_outreach(self, match):
        return {}


class RaisingProvider:
    name = "raising"

    def next_step(self, state):
        raise AppError(ErrorCode.provider_unavailable, "simulated outage")

    def generate_screening_questions(self, match, count):
        raise AppError(ErrorCode.provider_unavailable, "simulated outage")

    def draft_outreach(self, match):
        raise AppError(ErrorCode.provider_unavailable, "simulated outage")


def amira_and_backend_ids(db) -> tuple[int, int]:
    """Resolve Amira Haddad + Senior Backend Engineer ids dynamically.

    (Rowids keep incrementing across per-test reseeds — never hardcode 1.)
    """
    from sqlalchemy import select

    from app.models import Candidate, Job

    candidate = db.scalar(select(Candidate).where(Candidate.full_name == "Amira Haddad"))
    job = db.scalar(select(Job).where(Job.title == "Senior Backend Engineer"))
    return candidate.id, job.id
