"""Job lookup/search."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.models import Job


def search_jobs(db: Session, query: str | None = None, limit: int = 10) -> list[Job]:
    stmt = select(Job).order_by(Job.id)
    if query:
        like = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(Job.title.ilike(like), Job.company.ilike(like), Job.domain.ilike(like))
        )
    return list(db.scalars(stmt.limit(max(1, min(limit, 50)))))


def resolve_job(db: Session, identifier: str) -> Job:
    identifier = (identifier or "").strip()
    if not identifier:
        raise AppError(ErrorCode.validation_error, "Job identifier is required.")
    if identifier.isdigit():
        job = db.get(Job, int(identifier))
        if job is None:
            raise AppError(ErrorCode.entity_not_found, f"No job with id {identifier}.")
        return job

    matches = list(
        db.scalars(select(Job).where(Job.title.ilike(f"%{identifier}%")).order_by(Job.id))
    )
    if not matches:
        raise AppError(ErrorCode.entity_not_found, f"No job matches '{identifier}'.")
    if len(matches) > 1:
        titles = ", ".join(f"{j.title} (id {j.id})" for j in matches[:5])
        raise AppError(
            ErrorCode.ambiguous_entity,
            f"'{identifier}' matches {len(matches)} jobs: {titles}.",
            detail="Use a full title or job id.",
        )
    return matches[0]


def get_job_detail(db: Session, job_id: int) -> dict:
    job = db.get(Job, job_id)
    if job is None:
        raise AppError(ErrorCode.entity_not_found, f"No job with id {job_id}.")
    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "seniority": job.seniority,
        "domain": job.domain,
        "status": job.status,
        "requirements": [
            {
                "id": r.id,
                "kind": r.kind,
                "category": r.category,
                "label": r.label,
                "min_years": r.min_years,
            }
            for r in job.requirements
        ],
        "applications_count": len(job.applications),
    }
