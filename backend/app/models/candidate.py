"""Candidate + profile-side models."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.note import CandidateNote


class Candidate(Base, TimestampMixin):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200))
    headline: Mapped[str | None] = mapped_column(String(200))
    location: Mapped[str | None] = mapped_column(String(200))
    years_experience: Mapped[float | None] = mapped_column(Float)
    summary: Mapped[str | None] = mapped_column(Text)
    #: The stored resume source used for grounded, quotable evidence.
    resume_text: Mapped[str | None] = mapped_column(Text)
    source_filename: Mapped[str | None] = mapped_column(String(300))

    skills: Mapped[list[CandidateSkill]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", order_by="CandidateSkill.id"
    )
    experiences: Mapped[list[CandidateExperience]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", order_by="CandidateExperience.id"
    )
    applications: Mapped[list[Application]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    notes: Mapped[list[CandidateNote]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", order_by="CandidateNote.id"
    )


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))  # as found in the resume
    normalized_name: Mapped[str] = mapped_column(String(120), index=True)
    category: Mapped[str | None] = mapped_column(String(60))
    evidence: Mapped[str | None] = mapped_column(Text)  # verbatim line from the resume

    candidate: Mapped[Candidate] = relationship(back_populates="skills")


class CandidateExperience(Base):
    __tablename__ = "candidate_experiences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str | None] = mapped_column(String(200))
    company: Mapped[str | None] = mapped_column(String(200))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(default=False)
    description: Mapped[str | None] = mapped_column(Text)

    candidate: Mapped[Candidate] = relationship(back_populates="experiences")
