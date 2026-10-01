"""Explicit error model shared by tools, the orchestrator and the API."""

from __future__ import annotations

from enum import StrEnum


class ErrorCode(StrEnum):
    entity_not_found = "entity_not_found"
    ambiguous_entity = "ambiguous_entity"
    validation_error = "validation_error"
    approval_required = "approval_required"
    approval_rejected = "approval_rejected"
    tool_failed = "tool_failed"
    provider_unavailable = "provider_unavailable"
    max_steps_exceeded = "max_steps_exceeded"
    policy_blocked = "policy_blocked"


class AppError(Exception):
    """Raised by services/tools to produce a structured error."""

    def __init__(self, code: ErrorCode, message: str, detail: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail
