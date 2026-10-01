"""Append-only activity log — the recruiter-facing audit trail."""

from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ActivityEvent(Base, TimestampMixin):
    __tablename__ = "activity_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(40), index=True)
    # e.g. conversation_started | tool_executed | approval_requested |
    #      approval_approved | approval_rejected | note_added | stage_moved
    summary: Mapped[str] = mapped_column(Text)
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("agent_conversations.id", ondelete="SET NULL")
    )
    approval_id: Mapped[int | None] = mapped_column(
        ForeignKey("approval_requests.id", ondelete="SET NULL")
    )
    candidate_id: Mapped[int | None] = mapped_column(
        ForeignKey("candidates.id", ondelete="SET NULL")
    )
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"))
    application_id: Mapped[int | None] = mapped_column(
        ForeignKey("applications.id", ondelete="SET NULL")
    )
    payload: Mapped[dict | None] = mapped_column(JSON)
