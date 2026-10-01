"""Recruiter notes (human or agent-authored, both auditable)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.candidate import Candidate


class CandidateNote(Base, TimestampMixin):
    __tablename__ = "candidate_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    author: Mapped[str] = mapped_column(String(120), default="recruiter")
    #: "recruiter" for notes written directly by a human, "agent" for notes the
    #: agent proposed and a recruiter approved (see docs/AGENT_DESIGN.md §approval policy).
    source: Mapped[str] = mapped_column(String(20), default="recruiter")
    body: Mapped[str] = mapped_column(Text)

    candidate: Mapped[Candidate] = relationship(back_populates="notes")
