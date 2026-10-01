"""Matching-lite unit tests — determinism, statuses, evidence traceability."""

from __future__ import annotations

from app.models import Candidate, CandidateSkill, Job, JobRequirement
from app.services.matching import evaluate_pair


def make_candidate(db, *, name="Test Candidate", **overrides) -> Candidate:
    candidate = Candidate(
        full_name=name,
        headline=overrides.get("headline"),
        location=overrides.get("location"),
        years_experience=overrides.get("years"),
        summary=overrides.get("summary"),
        resume_text=overrides.get("resume_text"),
    )
    for skill, evidence in overrides.get("skills", []):
        candidate.skills.append(
            CandidateSkill(name=skill, normalized_name=skill, category=None, evidence=evidence)
        )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def make_job(db, requirements: list[dict], **overrides) -> Job:
    job = Job(
        title=overrides.get("title", "Test Job"),
        company="Test Co",
        domain=overrides.get("domain"),
    )
    for index, req in enumerate(requirements):
        job.requirements.append(
            JobRequirement(
                kind=req.get("kind", "must_have"),
                category=req["category"],
                label=req["label"],
                normalized_skill=req.get("skill"),
                keywords=req.get("keywords"),
                min_years=req.get("min_years"),
                order_index=index,
            )
        )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def test_skill_met_with_evidence(db):
    candidate = make_candidate(
        db,
        resume_text="Skills\nPython, FastAPI",
        skills=[("python", "- Built services in Python")],
    )
    job = make_job(db, [{"category": "skill", "label": "Python", "skill": "python"}])
    (result,) = evaluate_pair(candidate, job).requirements

    assert result.status == "met"
    assert result.evidence and result.evidence[0].snippet == "- Built services in Python"


def test_related_skill_partial_credit(db):
    candidate = make_candidate(
        db,
        resume_text="Built interfaces in React.",
        skills=[("react", "Built interfaces in React.")],
    )
    job = make_job(db, [{"category": "skill", "label": "Vue", "skill": "vue"}])
    (result,) = evaluate_pair(candidate, job).requirements

    assert result.status == "partial"
    assert "related skill" in result.reason.lower()


def test_experience_statuses(db):
    job_partial = make_job(
        db, [{"category": "experience", "label": "5+ years", "min_years": 5}], title="P"
    )
    job_missing = make_job(
        db, [{"category": "experience", "label": "10+ years", "min_years": 10}], title="M"
    )
    candidate = make_candidate(db, years=4.0, resume_text="…")
    assert evaluate_pair(candidate, job_partial).requirements[0].status == "partial"
    assert evaluate_pair(candidate, job_missing).requirements[0].status == "missing"

    unknown = make_candidate(db, name="NoYears")
    assert evaluate_pair(unknown, job_partial).requirements[0].status == "unknown"


def test_domain_unknown_when_no_evidence(db):
    candidate = make_candidate(db, resume_text="Nothing relevant here.")
    job = make_job(
        db,
        [{"category": "domain", "label": "Logistics", "keywords": ["logistics", "freight"]}],
    )
    (result,) = evaluate_pair(candidate, job).requirements
    assert result.status == "unknown"
    assert result.evidence == []


def test_determinism_same_inputs_same_output(db):
    candidate = make_candidate(
        db,
        resume_text="5 years in logistics. Python, Docker.",
        years=5.0,
        skills=[("python", "Python"), ("docker", "Docker")],
    )
    job = make_job(
        db,
        [
            {"category": "skill", "label": "Python", "skill": "python"},
            {"category": "skill", "label": "Docker", "skill": "docker"},
            {"category": "experience", "label": "3+ years", "min_years": 3},
        ],
    )
    first = evaluate_pair(candidate, job)
    second = evaluate_pair(candidate, job)
    assert first.score == second.score
    assert first.formula == second.formula
    assert [r.status for r in first.requirements] == [r.status for r in second.requirements]


def test_formula_is_published_and_renormalized(db):
    candidate = make_candidate(db, skills=[("python", None)], resume_text="python")
    job = make_job(db, [{"category": "skill", "label": "Python", "skill": "python"}])
    match = evaluate_pair(candidate, job)
    assert "re-normalized over present components" in match.formula
    assert match.score == 100.0


def test_seeded_evidence_is_traceable_to_resume_text(db):
    """The core evidence guarantee: what the agent quotes exists in the resume."""
    from sqlalchemy import select

    from app.models import Candidate as C
    from app.models import Job as J

    amira = db.scalar(select(C).where(C.full_name == "Amira Haddad"))
    job = db.scalar(select(J).where(J.title == "Senior Backend Engineer"))
    match = evaluate_pair(amira, job)

    checked = 0
    for result in match.requirements:
        for evidence in result.evidence:
            if evidence.source in ("skill_evidence", "resume_line"):
                checked += 1
                assert evidence.snippet in (amira.resume_text or ""), (
                    f"snippet not traceable: {evidence.snippet[:80]}"
                )
    assert checked >= 3  # the seeded pair must produce real quoted evidence


def test_no_protected_columns_in_schema():
    """Structural guard: no protected attribute can ever be stored."""
    import re

    import app.models  # noqa: F401
    from app.db.base import Base

    forbidden = (
        "age",
        "gender",
        "sex",
        "ethnic",
        "race",
        "religion",
        "disab",
        "marital",
        "photo",
        "national_id",
        "dob",
        "birth",
    )
    for table in Base.metadata.tables.values():
        for column in table.columns:
            name = column.name.lower()
            for term in forbidden:
                # Token-boundary match: 'stage' must not trip 'age'.
                if re.search(rf"(?:^|_){re.escape(term)}(?:_|$)", name):
                    raise AssertionError(f"protected column found: {table.name}.{name}")
