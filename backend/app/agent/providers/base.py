"""Provider plumbing shared by the demo agent and the OpenAI implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class Observation:
    """What the orchestrator hands back to the provider after a tool step."""

    tool: str
    ok: bool
    summary: str
    data: dict | None = None
    error_code: str | None = None
    args: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)
    call_ref: str | None = None  # provider-specific tool-call id (OpenAI)


@dataclass
class AgentState:
    """Everything the provider is allowed to see. No chain-of-thought anywhere."""

    user_message: str
    history: list[dict]  # recent [{role, content}] transcript (user/assistant only)
    observations: list[Observation]  # this turn, in order
    prior_observations: list[Observation]  # grounded context from earlier turns
    step: int = 1
    max_steps: int = 8
    max_tool_calls: int = 6
    tool_calls_made: int = 0


@dataclass
class ToolCall:
    name: str
    args: dict[str, Any]
    ref: str | None = None  # provider tool-call id, echoed into call_ref


@dataclass
class StepDecision:
    tool_call: ToolCall | None = None
    final_text: str | None = None


class Provider(Protocol):
    name: str  # "demo" | "openai"

    def next_step(self, state: AgentState) -> StepDecision: ...

    def generate_screening_questions(self, match: Any, count: int) -> list[dict]: ...

    def draft_outreach(self, match: Any) -> dict: ...
