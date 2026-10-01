"""Single execution path for tools — used by the orchestrator (reads/generations)
and by the approvals service (approved writes, exactly once).

Every execution:
1. re-validates arguments against the tool's input model,
2. runs the handler,
3. validates the result against the documented output contract,
4. returns a JSON-ready dict.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.tools.registry import ToolContext, ToolSpec, get_tool


@dataclass
class ExecutionOutcome:
    ok: bool
    result: dict | None
    error_code: str | None
    error_message: str | None
    duration_ms: int
    spec: ToolSpec | None


def execute_tool(db: Session, tool_name: str, raw_args: dict, ctx: ToolContext) -> ExecutionOutcome:
    started = time.monotonic()
    spec = get_tool(tool_name)
    if spec is None:
        return ExecutionOutcome(
            ok=False,
            result=None,
            error_code=ErrorCode.validation_error.value,
            error_message=f"Unknown tool '{tool_name}'. Available tools: "
            + ", ".join(sorted(s.name for s in _all_tools())),
            duration_ms=int((time.monotonic() - started) * 1000),
            spec=None,
        )

    try:
        params = spec.input_model.model_validate(raw_args)
    except ValidationError as exc:
        first = exc.errors()[0] if exc.errors() else {}
        return ExecutionOutcome(
            ok=False,
            result=None,
            error_code=ErrorCode.validation_error.value,
            error_message=(
                f"Invalid arguments for '{tool_name}': "
                f"{'.'.join(str(p) for p in first.get('loc', ()))}: {first.get('msg', 'invalid')}"
            ),
            duration_ms=int((time.monotonic() - started) * 1000),
            spec=spec,
        )

    try:
        raw_result = spec.handler(db, params, ctx)
    except AppError as exc:
        return ExecutionOutcome(
            ok=False,
            result=None,
            error_code=exc.code.value,
            error_message=exc.message,
            duration_ms=int((time.monotonic() - started) * 1000),
            spec=spec,
        )
    except Exception:  # pragma: no cover - defensive: never leak internals
        return ExecutionOutcome(
            ok=False,
            result=None,
            error_code=ErrorCode.tool_failed.value,
            error_message="The tool failed unexpectedly. Nothing was changed.",
            duration_ms=int((time.monotonic() - started) * 1000),
            spec=spec,
        )

    try:
        validated = spec.output_model.model_validate(raw_result)
    except ValidationError:
        return ExecutionOutcome(
            ok=False,
            result=None,
            error_code=ErrorCode.tool_failed.value,
            error_message="The tool returned data that failed its output contract.",
            duration_ms=int((time.monotonic() - started) * 1000),
            spec=spec,
        )

    return ExecutionOutcome(
        ok=True,
        result=validated.model_dump(),
        error_code=None,
        error_message=None,
        duration_ms=int((time.monotonic() - started) * 1000),
        spec=spec,
    )


def _all_tools():
    # Importing registers every tool exactly once.
    from app.tools.registry import REGISTRY

    return REGISTRY.values()
