"""The ten built-in tools — six reads, two generations, two controlled writes.

Writes NEVER execute through the agent loop: the orchestrator turns them into
ApprovalRequests and only the approvals service (backend-enforced) can execute
them, exactly once, after a human decision.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.models import ALL_STAGES, Candidate, Job
from app.services import candidates as candidates_service
from app.services import jobs as jobs_service
from app.services import notes as notes_service
from app.services import pipeline as pipeline_service
from app.services.generation import generate_outreach, generate_screening
from app.services.matching import evaluate_pair
from app.tools.contracts import (
    AddCandidateNoteInput,
    DraftOutreachInput,
    DraftOutreachOutput,
    GenerateScreeningInput,
    GenerateScreeningOutput,
    GetCandidateInput,
    GetCandidateOutput,
    GetJobInput,
    GetJobOutput,
    GetPipelineInput,
    GetPipelineOutput,
    MatchCandidateInput,
    MatchCandidateOutput,
    SearchCandidatesInput,
    SearchCandidatesOutput,
    SearchJobsInput,
    SearchJobsOutput,
    ToolStatusOutput,
    UpdatePipelineInput,
)
from app.tools.registry import (
    TOOL_KIND_GENERATION,
    TOOL_KIND_READ,
    TOOL_KIND_WRITE,
    ToolContext,
    ToolSpec,
    register,
)

# ── shapers ─────────────────────────────────────────────────────────────────


def _candidate_summary(candidate: Candidate, match_score: float | None = None) -> dict:
    return {
        "id": candidate.id,
        "full_name": candidate.full_name,
        "headline": candidate.headline,
        "location": candidate.location,
        "years_experience": candidate.years_experience,
        "skills": [s.normalized_name for s in candidate.skills][:12],
        "match_score": match_score,
    }


def _job_summary(job: Job) -> dict:
    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "status": job.status,
        "applications_count": len(job.applications),
    }


# ── READ tools ──────────────────────────────────────────────────────────────


def _search_candidates(db: Session, params: SearchCandidatesInput, ctx: ToolContext) -> dict:
    results = candidates_service.search_candidates(
        db, query=params.query, skill=params.skill, limit=params.limit
    )
    note = None
    if params.job_id is not None:
        try:
            job = jobs_service.resolve_job(db, str(params.job_id))
        except AppError as exc:
            raise exc
        ranked = []
        for candidate in results:
            match = evaluate_pair(candidate, job)
            ranked.append((match.score, candidate))
        ranked.sort(key=lambda pair: (-pair[0], pair[1].id))
        results = [c for _, c in ranked]
        candidates = [_candidate_summary(c, score) for score, c in ranked]
    else:
        candidates = [_candidate_summary(c) for c in results]

    if not candidates:
        note = "No candidates matched the filters."
    return {"candidates": candidates, "count": len(candidates), "note": note}


def _get_candidate(db: Session, params: GetCandidateInput, ctx: ToolContext) -> dict:
    candidate = candidates_service.resolve_candidate(db, params.identifier)
    return candidates_service.get_candidate_detail(db, candidate.id)


def _search_jobs(db: Session, params: SearchJobsInput, ctx: ToolContext) -> dict:
    results = jobs_service.search_jobs(db, query=params.query, limit=params.limit)
    jobs = [_job_summary(j) for j in results]
    return {"jobs": jobs, "count": len(jobs)}


def _get_job(db: Session, params: GetJobInput, ctx: ToolContext) -> dict:
    job = jobs_service.resolve_job(db, params.identifier)
    return jobs_service.get_job_detail(db, job.id)


def _match_candidate(db: Session, params: MatchCandidateInput, ctx: ToolContext) -> dict:
    candidate = db.get(Candidate, params.candidate_id)
    if candidate is None:
        raise AppError(ErrorCode.entity_not_found, f"No candidate with id {params.candidate_id}.")
    job = db.get(Job, params.job_id)
    if job is None:
        raise AppError(ErrorCode.entity_not_found, f"No job with id {params.job_id}.")
    match = evaluate_pair(candidate, job)
    return {
        "candidate_id": match.candidate_id,
        "candidate_name": match.candidate_name,
        "job_id": match.job_id,
        "job_title": match.job_title,
        "score": match.score,
        "components": match.components,
        "coverage": match.coverage,
        "formula": match.formula,
        "engine_version": match.engine_version,
        "requirements": [
            {
                "requirement_id": r.requirement_id,
                "kind": r.kind,
                "category": r.category,
                "label": r.label,
                "status": r.status,
                "reason": r.reason,
                "evidence": [{"snippet": e.snippet, "source": e.source} for e in r.evidence],
            }
            for r in match.requirements
        ],
    }


def _get_pipeline(db: Session, params: GetPipelineInput, ctx: ToolContext) -> dict:
    return pipeline_service.get_board(db, job_id=params.job_id)


# ── GENERATION tools ────────────────────────────────────────────────────────


def _generate_screening_questions(
    db: Session, params: GenerateScreeningInput, ctx: ToolContext
) -> dict:
    candidate = db.get(Candidate, params.candidate_id)
    if candidate is None:
        raise AppError(ErrorCode.entity_not_found, f"No candidate with id {params.candidate_id}.")
    job = db.get(Job, params.job_id)
    if job is None:
        raise AppError(ErrorCode.entity_not_found, f"No job with id {params.job_id}.")
    match = evaluate_pair(candidate, job)
    questions = generate_screening(match, count=params.count)
    return {
        "candidate_id": candidate.id,
        "candidate_name": candidate.full_name,
        "job_id": job.id,
        "job_title": job.title,
        "generated_by": questions["generated_by"],
        "questions": questions["questions"],
    }


def _draft_outreach(db: Session, params: DraftOutreachInput, ctx: ToolContext) -> dict:
    candidate = db.get(Candidate, params.candidate_id)
    if candidate is None:
        raise AppError(ErrorCode.entity_not_found, f"No candidate with id {params.candidate_id}.")
    job = db.get(Job, params.job_id)
    if job is None:
        raise AppError(ErrorCode.entity_not_found, f"No job with id {params.job_id}.")
    match = evaluate_pair(candidate, job)
    draft = generate_outreach(match)
    return {
        "candidate_id": candidate.id,
        "candidate_name": candidate.full_name,
        "job_id": job.id,
        "job_title": job.title,
        "generated_by": draft["generated_by"],
        "subject": draft["subject"],
        "body": draft["body"],
    }


# ── CONTROLLED WRITE tools (executed only via the approvals service) ───────


def _update_pipeline(db: Session, params: UpdatePipelineInput, ctx: ToolContext) -> dict:
    candidate = db.get(Candidate, params.candidate_id)
    if candidate is None:
        raise AppError(ErrorCode.entity_not_found, f"No candidate with id {params.candidate_id}.")
    job = db.get(Job, params.job_id)
    if job is None:
        raise AppError(ErrorCode.entity_not_found, f"No job with id {params.job_id}.")
    to_stage = params.to_stage.upper().strip()
    if to_stage not in ALL_STAGES:
        raise AppError(
            ErrorCode.validation_error,
            f"Unknown stage '{params.to_stage}'. Valid stages: {', '.join(ALL_STAGES)}.",
        )
    application = pipeline_service.ensure_application(db, candidate, job)
    moved = pipeline_service.move_application_stage(
        db,
        application,
        to_stage,
        note=params.note,
        actor=ctx.actor,
        approval_id=ctx.approval_id,
    )
    return {
        "ok": True,
        "message": (
            f"{moved['candidate_name']} moved {moved['from_stage']} → {moved['to_stage']} "
            f"for '{moved['job_title']}'."
        ),
        "data": moved,
    }


def _add_candidate_note(db: Session, params: AddCandidateNoteInput, ctx: ToolContext) -> dict:
    candidate = db.get(Candidate, params.candidate_id)
    if candidate is None:
        raise AppError(ErrorCode.entity_not_found, f"No candidate with id {params.candidate_id}.")
    note = notes_service.add_note(
        db,
        candidate,
        params.body,
        source="agent" if ctx.actor != "recruiter" else "recruiter",
        author="recruiting agent" if ctx.actor != "recruiter" else "recruiter",
        approval_id=ctx.approval_id,
    )
    return {
        "ok": True,
        "message": f"Note added to {candidate.full_name}.",
        "data": {"note_id": note.id, "candidate_id": candidate.id},
    }


# ── registration ────────────────────────────────────────────────────────────

register(
    ToolSpec(
        name="search_candidates",
        description=(
            "Search candidates by name/headline/location text and/or a canonical skill. "
            "Pass job_id to rank results by match score for that job."
        ),
        kind=TOOL_KIND_READ,
        requires_approval=False,
        input_model=SearchCandidatesInput,
        output_model=SearchCandidatesOutput,
        handler=_search_candidates,
    )
)
register(
    ToolSpec(
        name="get_candidate",
        description="Fetch one candidate profile by id or name. Errors if missing or ambiguous.",
        kind=TOOL_KIND_READ,
        requires_approval=False,
        input_model=GetCandidateInput,
        output_model=GetCandidateOutput,
        handler=_get_candidate,
    )
)
register(
    ToolSpec(
        name="search_jobs",
        description="Search jobs by title/company/domain substring.",
        kind=TOOL_KIND_READ,
        requires_approval=False,
        input_model=SearchJobsInput,
        output_model=SearchJobsOutput,
        handler=_search_jobs,
    )
)
register(
    ToolSpec(
        name="get_job",
        description="Fetch one job with its must-have/preferred requirements, by id or title.",
        kind=TOOL_KIND_READ,
        requires_approval=False,
        input_model=GetJobInput,
        output_model=GetJobOutput,
        handler=_get_job,
    )
)
register(
    ToolSpec(
        name="match_candidate",
        description=(
            "Deterministic, explainable match of one candidate against one job: "
            "per-requirement statuses, quoted evidence and the published formula."
        ),
        kind=TOOL_KIND_READ,
        requires_approval=False,
        input_model=MatchCandidateInput,
        output_model=MatchCandidateOutput,
        handler=_match_candidate,
    )
)
register(
    ToolSpec(
        name="get_pipeline",
        description="The pipeline board (stages → applications), optionally for one job.",
        kind=TOOL_KIND_READ,
        requires_approval=False,
        input_model=GetPipelineInput,
        output_model=GetPipelineOutput,
        handler=_get_pipeline,
    )
)
register(
    ToolSpec(
        name="generate_screening_questions",
        description=(
            "Generate job-related screening questions for a candidate/job pair, "
            "grounded in the match result. No protected/personal questions."
        ),
        kind=TOOL_KIND_GENERATION,
        requires_approval=False,
        input_model=GenerateScreeningInput,
        output_model=GenerateScreeningOutput,
        handler=_generate_screening_questions,
    )
)
register(
    ToolSpec(
        name="draft_outreach",
        description="Draft a short, honest outreach message for a candidate about a job.",
        kind=TOOL_KIND_GENERATION,
        requires_approval=False,
        input_model=DraftOutreachInput,
        output_model=DraftOutreachOutput,
        handler=_draft_outreach,
    )
)
register(
    ToolSpec(
        name="update_pipeline",
        description=(
            "Propose moving a candidate to a pipeline stage (creates the application "
            "if needed). REQUIRES recruiter approval before anything changes."
        ),
        kind=TOOL_KIND_WRITE,
        requires_approval=True,
        input_model=UpdatePipelineInput,
        output_model=ToolStatusOutput,
        handler=_update_pipeline,
        sensitive_arg_keys=("note",),
    )
)
register(
    ToolSpec(
        name="add_candidate_note",
        description=(
            "Propose adding a recruiter note to a candidate. REQUIRES recruiter "
            "approval before the note is stored."
        ),
        kind=TOOL_KIND_WRITE,
        requires_approval=True,
        input_model=AddCandidateNoteInput,
        output_model=ToolStatusOutput,
        handler=_add_candidate_note,
        sensitive_arg_keys=("body",),
    )
)
