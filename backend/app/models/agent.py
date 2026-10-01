"""Agent-side persistence: conversations, messages, tool executions, approvals."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from sqlalchemy import Session


class ApprovalStatus:
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTING = "EXECUTING"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"

    ALL = (PENDING, APPROVED, REJECTED, EXECUTING, EXECUTED, FAILED)


class ToolExecutionStatus:
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    REJECTED = "REJECTED"

    ALL = (SUCCEEDED, FAILED, AWAITING_APPROVAL, REJECTED)


class AgentConversation(Base, TimestampMixin):
    __tablename__ = "agent_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), default="New conversation")

    messages: Mapped[list[AgentMessage]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="AgentMessage.seq"
    )
    tool_executions: Mapped[list[ToolExecution]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    approvals: Mapped[list[ApprovalRequest]] = relationship(back_populates="conversation")


class AgentMessage(Base, TimestampMixin):
    __tablename__ = "agent_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("agent_conversations.id", ondelete="CASCADE"), index=True
    )
    seq: Mapped[int] = mapped_column(Integer)  # ordering within the conversation
    role: Mapped[str] = mapped_column(String(16))  # user | assistant | tool
    content: Mapped[str] = mapped_column(Text)
    #: For role="tool": the execution this message summarizes.
    tool_execution_id: Mapped[int | None] = mapped_column(
        ForeignKey("tool_executions.id", ondelete="SET NULL")
    )

    conversation: Mapped[AgentConversation] = relationship(back_populates="messages")


class ToolExecution(Base, TimestampMixin):
    __tablename__ = "tool_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("agent_conversations.id", ondelete="CASCADE"), index=True
    )
    step_number: Mapped[int] = mapped_column(Integer, default=1)
    tool_name: Mapped[str] = mapped_column(String(80))
    tool_kind: Mapped[str] = mapped_column(String(20))  # read | generation | write
    #: Sanitized argument summary (never raw resume bodies / PII — see SECURITY.md).
    args_json: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(24))  # ToolExecutionStatus.*
    error_code: Mapped[str | None] = mapped_column(String(40))
    result_summary: Mapped[str | None] = mapped_column(Text)  # short, safe summary
    #: Grounded context keys (job_id / candidate_id / top_candidate_id …) used
    #: to resolve follow-up references like "this candidate" without any
    #: reliance on model memory.
    meta_json: Mapped[dict | None] = mapped_column(JSON)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    approval_id: Mapped[int | None] = mapped_column(
        ForeignKey("approval_requests.id", ondelete="SET NULL")
    )

    conversation: Mapped[AgentConversation] = relationship(back_populates="tool_executions")


class ApprovalRequest(Base, TimestampMixin):
    __tablename__ = "approval_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("agent_conversations.id", ondelete="SET NULL"), index=True
    )
    tool_name: Mapped[str] = mapped_column(String(80))
    #: Exact validated arguments the tool will receive on approval.
    args_json: Mapped[dict] = mapped_column(JSON)
    summary: Mapped[str] = mapped_column(Text)  # human-readable "what will change"
    status: Mapped[str] = mapped_column(String(16), default=ApprovalStatus.PENDING, index=True)
    #: Unique key that makes approval execution exactly-once under retries.
    idempotency_key: Mapped[str] = mapped_column(String(120), unique=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[str | None] = mapped_column(String(120))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result_summary: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(40))

    conversation: Mapped[AgentConversation | None] = relationship(back_populates="approvals")


def conversations_with_messages(db: Session, conversation_id: int) -> AgentConversation | None:
    """Small helper kept here to avoid circular imports in routes."""
    return db.get(AgentConversation, conversation_id)
