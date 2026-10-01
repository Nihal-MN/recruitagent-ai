"""Seed runner — ``python -m app.seed [--reset]``.

Standalone from TalentFlow: 5 jobs, 20 candidates, pipeline states and notes,
all synthetic. Also composes each candidate's stored ``resume_text`` from the
same data, so every line of evidence the agent can quote is grounded in the
stored resume source.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import (
    ActivityEvent,
    AgentConversation,
    AgentMessage,
    Application,
    ApprovalRequest,
    Candidate,
    CandidateExperience,
    CandidateNote,
    CandidateSkill,
    Job,
    JobRequirement,
    ToolExecution,
)
from app.seed.demo_data import (
    APPLICATIONS,
    CANDIDATES,
    INJECTION_CANDIDATE,
    INJECTION_LINE,
    JOBS,
    RECRUITER_NOTES,
)
from app.services.skills import canonicalize, family_of

MONTHS = {
    "01": date(1, 1, 1),
}


def _parse_year(value: str | None, *, current_label: str) -> date | None:
    if value is None:
        return None
    if value.lower() in ("present", "current", "now") or value == current_label:
        return None
    return date(int(value), 1, 1)


def _compose_resume_text(candidate: dict) -> str:
    lines: list[str] = [
        candidate["name"],
        candidate["headline"],
        candidate["location"],
        "",
        "Summary",
        candidate["summary"],
        "",
        "Experience",
    ]
    evidence_lines = [evidence for _, evidence in candidate["skills"]]
    for index, (title, company, location, start, end, is_current) in enumerate(candidate["roles"]):
        end_label = "Present" if is_current else (end or "Present")
        lines.append(f"{title} — {company} ({location}) | {start} - {end_label}")
        if index == 0:
            lines.extend(evidence_lines)
        lines.append("")
    lines.append("Skills")
    lines.append(", ".join(name for name, _ in candidate["skills"]))
    if candidate["name"] == INJECTION_CANDIDATE:
        # Seeded prompt-injection scenario (documented in docs/EVALUATIONS.md and
        # RESPONSIBLE_AI.md): hostile text embedded in resume content must stay
        # data — it must never become an instruction.
        lines.extend(["", "Additional information", INJECTION_LINE])
    return "\n".join(lines)


def reset_all(db: Session) -> None:
    """Remove demo data in FK-safe order (never touches alembic_version)."""
    for model in (
        ActivityEvent,
        ToolExecution,
        ApprovalRequest,
        AgentMessage,
        AgentConversation,
        CandidateNote,
        Application,
        JobRequirement,
        Job,
        CandidateSkill,
        CandidateExperience,
        Candidate,
    ):
        db.execute(delete(model))
    db.commit()


def seed(db: Session) -> dict:
    job_models: dict[str, Job] = {}
    for job_data in JOBS:
        job = Job(
            title=job_data["title"],
            company=job_data["company"],
            location=job_data["location"],
            employment_type=job_data["employment_type"],
            seniority=job_data["seniority"],
            domain=job_data["domain"],
            description_text=job_data["description_text"],
            status="open",
        )
        for index, req in enumerate(job_data["requirements"]):
            keywords = req.get("keywords")
            skill = req.get("skill")
            if skill and not keywords:
                keywords = [skill]
            job.requirements.append(
                JobRequirement(
                    kind=req["kind"],
                    category=req["category"],
                    label=req["label"],
                    normalized_skill=canonicalize(skill) if skill else None,
                    keywords=keywords,
                    min_years=req.get("min_years"),
                    order_index=index,
                )
            )
        db.add(job)
        job_models[job_data["title"]] = job
    db.flush()

    candidate_models: dict[str, Candidate] = {}
    for data in CANDIDATES:
        candidate = Candidate(
            full_name=data["name"],
            headline=data["headline"],
            location=data["location"],
            years_experience=data["years"],
            summary=data["summary"],
            resume_text=_compose_resume_text(data),
            source_filename=data["name"].lower().replace(" ", "_") + ".resume.txt",
        )
        for name, evidence in data["skills"]:
            candidate.skills.append(
                CandidateSkill(
                    name=name,
                    normalized_name=canonicalize(name),
                    category=family_of(canonicalize(name)) or "general",
                    evidence=evidence,
                )
            )
        for title, company, _location, start, end, is_current in data["roles"]:
            candidate.experiences.append(
                CandidateExperience(
                    title=title,
                    company=company,
                    start_date=_parse_year(start, current_label=""),
                    end_date=None if is_current else _parse_year(end, current_label=""),
                    is_current=is_current,
                )
            )
        db.add(candidate)
        candidate_models[data["name"]] = candidate
    db.flush()

    for candidate_name, job_title, stage in APPLICATIONS:
        db.add(
            Application(
                candidate_id=candidate_models[candidate_name].id,
                job_id=job_models[job_title].id,
                stage=stage,
            )
        )
    for candidate_name, body, source in RECRUITER_NOTES:
        db.add(
            CandidateNote(
                candidate_id=candidate_models[candidate_name].id,
                body=body,
                source=source,
                author="recruiter",
            )
        )
    db.commit()

    return {
        "jobs": len(JOBS),
        "candidates": len(CANDIDATES),
        "applications": len(APPLICATIONS),
        "notes": len(RECRUITER_NOTES),
    }


def main(reset: bool = False) -> None:
    with SessionLocal() as db:
        if reset:
            reset_all(db)
        summary = seed(db)
    print(
        "Seeded demo dataset: "
        + ", ".join(f"{value} {key}" for key, value in summary.items())
        + "."
    )
    if reset:
        print("(reset: previous demo data removed)")


if __name__ == "__main__":
    main()
