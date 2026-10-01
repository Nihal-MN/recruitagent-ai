"""Candidate lookup/search — the read path the agent grounds itself in."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.models import Candidate, CandidateSkill


def search_candidates(
    db: Session,
    query: str | None = None,
    skill: str | None = None,
    limit: int = 10,
) -> list[Candidate]:
    stmt = select(Candidate).order_by(Candidate.id)
    if query:
        like = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                Candidate.full_name.ilike(like),
                Candidate.headline.ilike(like),
                Candidate.summary.ilike(like),
                Candidate.location.ilike(like),
            )
        )
    if skill:
        stmt = (
            stmt.join(CandidateSkill, CandidateSkill.candidate_id == Candidate.id)
            .where(CandidateSkill.normalized_name == skill)
            .distinct()
        )
    return list(db.scalars(stmt.limit(max(1, min(limit, 50)))))


def resolve_candidate(db: Session, identifier: str) -> Candidate:
    """Resolve an id-or-name identifier exactly once.

    - numeric → direct id lookup
    - otherwise → case-insensitive substring on full name
    - 0 matches → entity_not_found; >1 → ambiguous_entity (caller shows options)
    """
    identifier = (identifier or "").strip()
    if not identifier:
        raise AppError(ErrorCode.validation_error, "Candidate identifier is required.")
    if identifier.isdigit():
        candidate = db.get(Candidate, int(identifier))
        if candidate is None:
            raise AppError(ErrorCode.entity_not_found, f"No candidate with id {identifier}.")
        return candidate

    matches = list(
        db.scalars(
            select(Candidate)
            .where(Candidate.full_name.ilike(f"%{identifier}%"))
            .order_by(Candidate.id)
        )
    )
    if not matches:
        raise AppError(ErrorCode.entity_not_found, f"No candidate matches '{identifier}'.")
    if len(matches) > 1:
        names = ", ".join(f"{c.full_name} (id {c.id})" for c in matches[:5])
        raise AppError(
            ErrorCode.ambiguous_entity,
            f"'{identifier}' matches {len(matches)} candidates: {names}.",
            detail="Use a full name or candidate id.",
        )
    return matches[0]


def get_candidate_detail(db: Session, candidate_id: int) -> dict:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise AppError(ErrorCode.entity_not_found, f"No candidate with id {candidate_id}.")
    return {
        "id": candidate.id,
        "full_name": candidate.full_name,
        "headline": candidate.headline,
        "location": candidate.location,
        "years_experience": candidate.years_experience,
        "summary": candidate.summary,
        "skills": [
            {
                "name": s.name,
                "normalized_name": s.normalized_name,
                "category": s.category,
                "evidence": s.evidence,
            }
            for s in candidate.skills
        ],
        "experiences": [
            {
                "title": e.title,
                "company": e.company,
                "start_date": e.start_date.isoformat() if e.start_date else None,
                "end_date": e.end_date.isoformat() if e.end_date else None,
                "is_current": e.is_current,
            }
            for e in candidate.experiences
        ],
        "applications": [
            {"id": a.id, "job_id": a.job_id, "job_title": a.job.title, "stage": a.stage}
            for a in candidate.applications
        ],
        "notes_count": len(candidate.notes),
    }
