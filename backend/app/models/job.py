"""Job + requirement models."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application

JOB_STATUSES = ("open", "closed")


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    company: Mapped[str | None] = mapped_column(String(200))
    location: Mapped[str | None] = mapped_column(String(200))
    employment_type: Mapped[str | None] = mapped_column(String(60))
    seniority: Mapped[str | None] = mapped_column(String(40))
    domain: Mapped[str | None] = mapped_column(String(60))
    description_text: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open")

    requirements: Mapped[list[JobRequirement]] = relationship(
        back_populates="job", cascade="all, delete-orphan", order_by="JobRequirement.order_index"
    )
    applications: Mapped[list[Application]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class JobRequirement(Base):
    __tablename__ = "job_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="must_have")  # must_have | preferred
    category: Mapped[str] = mapped_column(String(40))  # skill|experience|domain|location|other
    label: Mapped[str] = mapped_column(Text)
    normalized_skill: Mapped[str | None] = mapped_column(String(120))
    keywords: Mapped[list | None] = mapped_column(JSON)
    min_years: Mapped[float | None] = mapped_column(Float)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    job: Mapped[Job] = relationship(back_populates="requirements")
