"""Candidates + jobs read APIs for the UI (agent uses tools instead)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import func, select

from app.api.deps import DbSession
from app.api.schemas import CandidateListItem
from app.models import Application, Candidate
from app.services import candidates as candidates_service
from app.services import jobs as jobs_service

router = APIRouter()


@router.get("/candidates", response_model=list[CandidateListItem], summary="List candidates")
def list_candidates(
    response: Response,
    db: DbSession,
    query: str | None = Query(None, max_length=120),
    skill: str | None = Query(None, max_length=60),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[CandidateListItem]:
    total_stmt = select(func.count(Candidate.id))
    if query:
        like = f"%{query.strip()}%"
        total_stmt = total_stmt.where(Candidate.full_name.ilike(like))
    total = db.scalar(total_stmt) or 0
    response.headers["X-Total-Count"] = str(total)

    results = candidates_service.search_candidates(db, query=query, skill=skill, limit=limit)
    items: list[CandidateListItem] = []
    for candidate in results[offset:]:
        application = db.scalar(
            select(Application)
            .where(Application.candidate_id == candidate.id)
            .order_by(Application.updated_at.desc())
            .limit(1)
        )
        items.append(
            CandidateListItem(
                id=candidate.id,
                full_name=candidate.full_name,
                headline=candidate.headline,
                location=candidate.location,
                years_experience=candidate.years_experience,
                skills=[s.normalized_name for s in candidate.skills][:12],
                in_pipeline=application.stage if application else None,
            )
        )
    return items


@router.get("/candidates/{candidate_id}", summary="Candidate detail with evidence + notes")
def candidate_detail(candidate_id: int, db: DbSession) -> dict:
    try:
        detail = candidates_service.get_candidate_detail(db, candidate_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    candidate = db.get(Candidate, candidate_id)
    detail["notes"] = [
        {
            "id": n.id,
            "body": n.body,
            "source": n.source,
            "author": n.author,
            "created_at": n.created_at.isoformat(),
        }
        for n in (candidate.notes if candidate else [])
    ]
    return detail


@router.get("/jobs", summary="List jobs")
def list_jobs(db: DbSession, limit: int = Query(50, ge=1, le=100)) -> list[dict]:
    jobs = jobs_service.search_jobs(db, limit=limit)
    return [
        {
            "id": j.id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "seniority": j.seniority,
            "domain": j.domain,
            "status": j.status,
            "requirements_count": len(j.requirements),
            "applications_count": len(j.applications),
        }
        for j in jobs
    ]


@router.get("/jobs/{job_id}", summary="Job detail with requirements")
def job_detail(job_id: int, db: DbSession) -> dict:
    try:
        return jobs_service.get_job_detail(db, job_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
