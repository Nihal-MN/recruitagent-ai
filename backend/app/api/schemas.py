"""Pydantic schemas for the public API (request + response contracts)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str | None = Field(None, max_length=120)


class MessageIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    seq: int
    created_at: datetime


class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ToolExecutionOut(BaseModel):
    id: int
    conversation_id: int
    step_number: int
    tool_name: str
    tool_kind: str
    args_json: dict | None = None
    status: str
    error_code: str | None = None
    result_summary: str | None = None
    duration_ms: int | None = None
    approval_id: int | None = None
    created_at: datetime


class ApprovalOut(BaseModel):
    id: int
    conversation_id: int | None = None
    tool_name: str
    args_json: dict
    summary: str
    status: str
    decided_at: datetime | None = None
    decided_by: str | None = None
    executed_at: datetime | None = None
    result_summary: str | None = None
    error_code: str | None = None
    created_at: datetime


class TurnResult(BaseModel):
    conversation_id: int
    final_text: str
    stopped_reason: str
    message_ids: list[int]
    tool_execution_ids: list[int]
    approval_ids: list[int]
    error_code: str | None = None


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = Field(default_factory=list)
    tool_executions: list[ToolExecutionOut] = Field(default_factory=list)
    approvals: list[ApprovalOut] = Field(default_factory=list)


class CandidateListItem(BaseModel):
    id: int
    full_name: str
    headline: str | None = None
    location: str | None = None
    years_experience: float | None = None
    skills: list[str] = Field(default_factory=list)
    in_pipeline: str | None = None


class ApprovalDecision(BaseModel):
    decided_by: str = Field("recruiter", max_length=120)


class ActivityOut(BaseModel):
    id: int
    type: str
    summary: str
    conversation_id: int | None = None
    approval_id: int | None = None
    candidate_id: int | None = None
    job_id: int | None = None
    application_id: int | None = None
    payload: dict | None = None
    created_at: datetime
