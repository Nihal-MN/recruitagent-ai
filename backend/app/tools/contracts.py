"""Strict Pydantic input/output contracts for every agent tool.

These schemas are the single source of truth: the orchestrator validates
incoming arguments against ``*Input`` before any execution, the executor
validates handler results against ``*Output`` before the model ever sees them,
and docs/TOOLS.md is generated from these definitions.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ── Inputs ──────────────────────────────────────────────────────────────────


class SearchCandidatesInput(_Base):
    query: str | None = Field(None, max_length=120, description="Name/headline/location substring.")
    skill: str | None = Field(None, max_length=60, description="Canonical skill to require.")
    job_id: int | None = Field(None, description="Rank results by match score for this job.")
    limit: int = Field(10, ge=1, le=20)


class GetCandidateInput(_Base):
    identifier: str = Field(..., min_length=1, max_length=120, description="Candidate id or name.")


class SearchJobsInput(_Base):
    query: str | None = Field(None, max_length=120, description="Title/company/domain substring.")
    limit: int = Field(10, ge=1, le=20)


class GetJobInput(_Base):
    identifier: str = Field(..., min_length=1, max_length=120, description="Job id or title.")


class MatchCandidateInput(_Base):
    candidate_id: int = Field(..., ge=1)
    job_id: int = Field(..., ge=1)


class GetPipelineInput(_Base):
    job_id: int | None = Field(None, ge=1, description="Restrict the board to one job.")


class GenerateScreeningInput(_Base):
    candidate_id: int = Field(..., ge=1)
    job_id: int = Field(..., ge=1)
    count: int = Field(6, ge=1, le=10)


class DraftOutreachInput(_Base):
    candidate_id: int = Field(..., ge=1)
    job_id: int = Field(..., ge=1)


class UpdatePipelineInput(_Base):
    candidate_id: int = Field(..., ge=1)
    job_id: int = Field(..., ge=1)
    to_stage: str = Field(
        ..., description="NEW | SCREENING | SHORTLISTED | INTERVIEW | OFFER | HIRED | REJECTED"
    )
    note: str | None = Field(None, max_length=300)


class AddCandidateNoteInput(_Base):
    candidate_id: int = Field(..., ge=1)
    body: str = Field(..., min_length=1, max_length=2000)


# ── Outputs ─────────────────────────────────────────────────────────────────


class CandidateSummary(_Base):
    id: int
    full_name: str
    headline: str | None = None
    location: str | None = None
    years_experience: float | None = None
    skills: list[str] = Field(default_factory=list)
    match_score: float | None = None


class SearchCandidatesOutput(_Base):
    candidates: list[CandidateSummary]
    count: int
    note: str | None = None  # e.g. an ambiguity or empty-result hint


class SkillOut(_Base):
    name: str
    normalized_name: str
    category: str | None = None
    evidence: str | None = None


class ExperienceOut(_Base):
    title: str | None = None
    company: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool = False


class ApplicationOut(_Base):
    id: int
    job_id: int
    job_title: str
    stage: str


class GetCandidateOutput(_Base):
    id: int
    full_name: str
    headline: str | None = None
    location: str | None = None
    years_experience: float | None = None
    summary: str | None = None
    skills: list[SkillOut] = Field(default_factory=list)
    experiences: list[ExperienceOut] = Field(default_factory=list)
    applications: list[ApplicationOut] = Field(default_factory=list)
    notes_count: int = 0


class JobSummary(_Base):
    id: int
    title: str
    company: str | None = None
    location: str | None = None
    status: str = "open"
    applications_count: int | None = None


class SearchJobsOutput(_Base):
    jobs: list[JobSummary]
    count: int


class RequirementOut(_Base):
    id: int
    kind: str
    category: str
    label: str
    min_years: float | None = None


class GetJobOutput(_Base):
    id: int
    title: str
    company: str | None = None
    location: str | None = None
    seniority: str | None = None
    domain: str | None = None
    status: str
    requirements: list[RequirementOut] = Field(default_factory=list)
    applications_count: int = 0


class EvidenceOut(_Base):
    snippet: str
    source: str


class RequirementResultOut(_Base):
    requirement_id: int
    kind: str
    category: str
    label: str
    status: str
    reason: str
    evidence: list[EvidenceOut] = Field(default_factory=list)


class MatchCandidateOutput(_Base):
    candidate_id: int
    candidate_name: str
    job_id: int
    job_title: str
    score: float
    components: dict[str, float | None]
    coverage: dict[str, int]
    formula: str
    engine_version: str
    requirements: list[RequirementResultOut] = Field(default_factory=list)


class PipelineItem(_Base):
    application_id: int
    candidate_id: int
    candidate_name: str
    job_id: int
    job_title: str
    stage: str
    updated_at: str


class GetPipelineOutput(_Base):
    columns: dict[str, list[PipelineItem]]
    total: int


class ScreeningQuestionOut(_Base):
    question: str
    rationale: str
    category: str  # strength_probe | gap_probe | behavioral | role_fit


class GenerateScreeningOutput(_Base):
    candidate_id: int
    candidate_name: str
    job_id: int
    job_title: str
    generated_by: str  # demo | openai
    questions: list[ScreeningQuestionOut]


class DraftOutreachOutput(_Base):
    candidate_id: int
    candidate_name: str
    job_id: int
    job_title: str
    generated_by: str
    subject: str
    body: str


class ToolStatusOutput(_Base):
    """Generic result for write tools (also used in approval previews)."""

    ok: bool = True
    message: str
    data: dict = Field(default_factory=dict)
