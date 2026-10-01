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

    #: code → HTTP status for the API layer
    HTTP_STATUS = {
        ErrorCode.entity_not_found: 404,
        ErrorCode.ambiguous_entity: 409,
        ErrorCode.validation_error: 422,
        ErrorCode.approval_required: 409,
        ErrorCode.approval_rejected: 409,
        ErrorCode.tool_failed: 500,
        ErrorCode.provider_unavailable: 503,
        ErrorCode.max_steps_exceeded: 429,
        ErrorCode.policy_blocked: 409,
    }

    def __init__(self, code: ErrorCode, message: str, detail: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail

    @property
    def http_status(self) -> int:
        return self.HTTP_STATUS.get(self.code, 400)
