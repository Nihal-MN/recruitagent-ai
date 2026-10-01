"""Tool registry — the ONLY capabilities the agent can ever invoke.

Design rules (see docs/TOOLS.md):

- reads are free; generations are free; **writes require approval**;
- every tool has strict Pydantic input validation and a documented output
  contract; results are validated before they reach the model;
- the model never touches the database — it can only call these functions.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from app.core.errors import AppError, ErrorCode

TOOL_KIND_READ = "read"
TOOL_KIND_GENERATION = "generation"
TOOL_KIND_WRITE = "write"


@dataclass(frozen=True)
class ToolContext:
    """Ambient execution context (never model-controlled)."""

    conversation_id: int | None = None
    actor: str = "agent"
    approval_id: int | None = None


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    kind: str
    requires_approval: bool
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    handler: Callable[..., dict]
    sensitive_arg_keys: tuple[str, ...] = field(default=())

    def summarizes_as(self, result: dict) -> str:
        """Short, safe summary of a result for traces (no bodies, no PII dumps)."""
        if "count" in result and "candidates" in result:
            return f"{result['count']} candidate(s) returned"
        if "count" in result and "jobs" in result:
            return f"{result['count']} job(s) returned"
        if "candidates" in result:
            return f"{len(result['candidates'])} candidate(s) returned"
        if "questions" in result:
            return f"{len(result['questions'])} screening question(s) generated"
        if "subject" in result:
            return "outreach draft generated"
        if "score" in result and "candidate_name" in result:
            return f"match {result['score']}/100 for {result['candidate_name']}"
        if "columns" in result:
            return f"pipeline board: {result.get('total', 0)} application(s)"
        if "full_name" in result:
            return f"profile: {result['full_name']}"
        if "title" in result:
            return f"job: {result['title']}"
        if "message" in result:
            return str(result["message"])[:140]
        return "ok"


REGISTRY: dict[str, ToolSpec] = {}


def register(spec: ToolSpec) -> ToolSpec:
    if spec.name in REGISTRY:
        raise RuntimeError(f"Tool '{spec.name}' already registered")
    REGISTRY[spec.name] = spec
    return spec


def get_tool(name: str) -> ToolSpec | None:
    return REGISTRY.get(name)


def tool_descriptors() -> list[dict[str, Any]]:
    """Provider-agnostic descriptors (used for prompts + docs)."""
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "kind": spec.kind,
            "requires_approval": spec.requires_approval,
            "input_schema": spec.input_model.model_json_schema(),
        }
        for spec in REGISTRY.values()
    ]


def summarize_tool_error(exc: Exception) -> tuple[str, str]:
    """Map any exception to (error_code, safe message)."""
    if isinstance(exc, AppError):
        return exc.code.value, exc.message
    return ErrorCode.tool_failed.value, "The tool failed unexpectedly. Nothing was changed."


def sanitize_args(spec: ToolSpec, params: BaseModel) -> dict:
    """Trace-safe argument rendering: truncate strings, drop nothing else."""
    data = params.model_dump(exclude_none=True)
    safe: dict = {}
    for key, value in data.items():
        if isinstance(value, str) and len(value) > 140:
            safe[key] = value[:137] + "…"
        else:
            safe[key] = value
    return safe
