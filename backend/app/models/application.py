"""Application (candidate ↔ job) with a real pipeline and audit trail."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.job import Job

#: Ordered pipeline; REJECTED is an off-ramp.
STAGES = ("NEW", "SCREENING", "SHORTLISTED", "INTERVIEW", "OFFER", "HIRED")
OFF_RAMPS = ("REJECTED",)
ALL_STAGES = STAGES + OFF_RAMPS


class Application(Base, TimestampMixin):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("candidate_id", "job_id", name="uq_application_pair"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(20), default="NEW")

    candidate: Mapped[Candidate] = relationship(back_populates="applications")
    job: Mapped[Job] = relationship(back_populates="applications")
