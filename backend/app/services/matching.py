"""Deterministic matching-lite — grounding for the agent, not an opaque ranker.

Every result is requirement-by-requirement with a written reason and quoted,
traceable evidence. The LLM is NEVER the ranking engine; if the agent talks
about a match, it must come from this module's output. Weights are published:

- must-have requirements: 0.60
- preferred requirements: 0.20
- experience (years):     0.10
- domain:                 0.10

re-normalized over the components that are present. Status scores:
met = 1.0, partial = 0.5, missing = 0.0, unknown → excluded from scoring.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.models.candidate import Candidate
from app.models.job import Job
from app.services.skills import are_related, canonicalize, mention_in_text

ENGINE_VERSION = "matching-lite-v1"
WEIGHTS = {"must_have": 0.60, "preferred": 0.20, "experience": 0.10, "domain": 0.10}
STATUS_SCORES = {"met": 1.0, "partial": 0.5, "missing": 0.0}
PARTIAL_YEARS_RATIO = 0.75  # within 75% of the requirement counts as partial


@dataclass(slots=True)
class Evidence:
    snippet: str
    source: str  # "resume_line" | "skill_evidence" | "computed" | "profile"


@dataclass(slots=True)
class RequirementResult:
    requirement_id: int
    kind: str
    category: str
    label: str
    status: str  # met | partial | missing | unknown
    reason: str
    evidence: list[Evidence] = field(default_factory=list)


@dataclass(slots=True)
class MatchResult:
    candidate_id: int
    candidate_name: str
    job_id: int
    job_title: str
    score: float
    components: dict[str, float | None]
    coverage: dict[str, int]
    formula: str
    engine_version: str = ENGINE_VERSION
    requirements: list[RequirementResult] = field(default_factory=list)


def _resume_line_for(term: str, resume_text: str | None) -> str | None:
    """Return the first resume line containing the term (verbatim)."""
    if not resume_text:
        return None
    for raw in resume_text.splitlines():
        line = raw.strip()
        if line and mention_in_text(term, line):
            return line[:300]
    return None


def _skill_map(candidate: Candidate) -> dict[str, str | None]:
    return {skill.normalized_name: skill.evidence for skill in candidate.skills}


def _evaluate_requirement(candidate: Candidate, requirement) -> RequirementResult:
    category = requirement.category
    kind = requirement.kind
    target = requirement.normalized_skill or (
        canonicalize(requirement.label) if category == "skill" else None
    )

    if category == "skill" and target:
        skills = _skill_map(candidate)
        if target in skills:
            evidence = []
            evidence_line = skills[target]
            if evidence_line:
                evidence.append(Evidence(snippet=evidence_line, source="skill_evidence"))
            return RequirementResult(
                requirement.id,
                kind,
                category,
                requirement.label,
                "met",
                f"'{target}' is on the candidate's profile.",
                evidence,
            )
        line = _resume_line_for(target, candidate.resume_text)
        if line:
            return RequirementResult(
                requirement.id,
                kind,
                category,
                requirement.label,
                "met",
                f"'{target}' appears in the resume text.",
                [Evidence(line, "resume_line")],
            )
        related = [s for s in skills if are_related(target, s)]
        if related:
            evidence = [
                Evidence(
                    _resume_line_for(s, candidate.resume_text) or f"Related skill: {s}",
                    "resume_line",
                )
                for s in related[:2]
            ]
            return RequirementResult(
                requirement.id,
                kind,
                category,
                requirement.label,
                "partial",
                f"No '{target}', but related skill(s) in the same family: "
                f"{', '.join(related[:3])}. Related skills earn partial credit only.",
                evidence,
            )
        return RequirementResult(
            requirement.id,
            kind,
            category,
            requirement.label,
            "missing",
            f"No evidence of '{target}' in the profile or resume.",
            [],
        )

    if category == "experience":
        min_years = requirement.min_years
        years = candidate.years_experience
        if min_years is None or years is None:
            return RequirementResult(
                requirement.id,
                kind,
                category,
                requirement.label,
                "unknown",
                "Years of experience could not be compared (missing data).",
                [],
            )
        computed = Evidence(
            f"{years:g} years of experience vs required {min_years:g} (computed from resume dates)",
            "computed",
        )
        if years >= min_years:
            return RequirementResult(
                requirement.id,
                kind,
                category,
                requirement.label,
                "met",
                f"{years:g} years meets the {min_years:g}+ years requirement.",
                [computed],
            )
        if years >= min_years * PARTIAL_YEARS_RATIO:
            return RequirementResult(
                requirement.id,
                kind,
                category,
                requirement.label,
                "partial",
                f"{years:g} years is close to the required {min_years:g}+ years.",
                [computed],
            )
        return RequirementResult(
            requirement.id,
            kind,
            category,
            requirement.label,
            "missing",
            f"{years:g} years vs required {min_years:g}+ years.",
            [computed],
        )

    if category == "domain":
        keywords = requirement.keywords or []
        for keyword in keywords:
            line = _resume_line_for(keyword, candidate.resume_text)
            if line:
                return RequirementResult(
                    requirement.id,
                    kind,
                    category,
                    requirement.label,
                    "met",
                    f"Domain evidence found: '{keyword}'.",
                    [Evidence(line, "resume_line")],
                )
        summary_text = (candidate.summary or "").lower()
        if summary_text and any(keyword.lower() in summary_text for keyword in keywords):
            return RequirementResult(
                requirement.id,
                kind,
                category,
                requirement.label,
                "met",
                "Domain signal found on the profile summary.",
                [Evidence((candidate.summary or "")[:220], "profile")],
            )
        return RequirementResult(
            requirement.id,
            kind,
            category,
            requirement.label,
            "unknown",
            "No domain evidence found on the profile.",
            [],
        )

    if category == "location":
        if requirement.label and "remote" in requirement.label.lower():
            return RequirementResult(
                requirement.id,
                kind,
                category,
                requirement.label,
                "met",
                "The role is remote-friendly.",
                [Evidence(requirement.label[:120], "profile")],
            )
        keywords = requirement.keywords or []
        candidate_location = (candidate.location or "").lower()
        for keyword in keywords:
            if keyword.lower() in candidate_location:
                return RequirementResult(
                    requirement.id,
                    kind,
                    category,
                    requirement.label,
                    "met",
                    f"Candidate location '{candidate.location}' matches.",
                    [Evidence(candidate.location or "", "profile")],
                )
        if candidate_location:
            return RequirementResult(
                requirement.id,
                kind,
                category,
                requirement.label,
                "missing",
                f"Candidate location '{candidate.location}' does not match.",
                [],
            )
        return RequirementResult(
            requirement.id,
            kind,
            category,
            requirement.label,
            "unknown",
            "Candidate location is unknown.",
            [],
        )

    # other / education-like niche requirements — keyword presence in the resume
    keywords = requirement.keywords or []
    for keyword in keywords:
        line = _resume_line_for(keyword, candidate.resume_text)
        if line:
            return RequirementResult(
                requirement.id,
                kind,
                category,
                requirement.label,
                "met",
                f"'{keyword}' found in the resume.",
                [Evidence(line, "resume_line")],
            )
    return RequirementResult(
        requirement.id,
        kind,
        category,
        requirement.label,
        "unknown",
        "Nothing on the profile speaks to this requirement.",
        [],
    )


def _aggregate(results: list[RequirementResult]) -> dict[str, float | None]:
    """Mean status score per scoring component (unknown excluded)."""
    components: dict[str, float | None] = {}
    for component in ("must_have", "preferred"):
        rows = [r for r in results if r.kind == component and r.category in ("skill", "other")]
        scored = [STATUS_SCORES[r.status] for r in rows if r.status in STATUS_SCORES]
        components[component] = (sum(scored) / len(scored)) if scored else None

    experience_rows = [r for r in results if r.category == "experience"]
    exp = [STATUS_SCORES[r.status] for r in experience_rows if r.status in STATUS_SCORES]
    components["experience"] = (sum(exp) / len(exp)) if exp else None

    domain_rows = [r for r in results if r.category == "domain"]
    dom = [STATUS_SCORES[r.status] for r in domain_rows if r.status in STATUS_SCORES]
    components["domain"] = (sum(dom) / len(dom)) if dom else None
    return components


def evaluate_pair(candidate: Candidate, job: Job) -> MatchResult:
    """Evaluate one candidate against one job. Deterministic and side-effect free."""
    results = [_evaluate_requirement(candidate, req) for req in job.requirements]
    components = _aggregate(results)

    present = {k: v for k, v in components.items() if v is not None}
    weight_total = sum(WEIGHTS[k] for k in present)
    if weight_total > 0:
        score = 100.0 * sum(WEIGHTS[k] * v for k, v in present.items()) / weight_total
    else:
        score = 0.0

    coverage = {
        "must_have_met": sum(1 for r in results if r.kind == "must_have" and r.status == "met"),
        "must_have_partial": sum(
            1 for r in results if r.kind == "must_have" and r.status == "partial"
        ),
        "must_have_missing": sum(
            1 for r in results if r.kind == "must_have" and r.status == "missing"
        ),
        "preferred_met": sum(1 for r in results if r.kind == "preferred" and r.status == "met"),
    }

    formula_parts = []
    for key in ("must_have", "preferred", "experience", "domain"):
        value = components.get(key)
        if value is not None:
            share = WEIGHTS[key] / weight_total if weight_total else 0
            formula_parts.append(f"{share:.2f}·{key}[{value * 100:.0f}%]")
    formula = (
        " + ".join(formula_parts)
        + f" = {score:.1f}/100 (weights re-normalized over present components)"
        if formula_parts
        else "No scorable components."
    )

    return MatchResult(
        candidate_id=candidate.id,
        candidate_name=candidate.full_name,
        job_id=job.id,
        job_title=job.title,
        score=round(score, 1),
        components=components,
        coverage=coverage,
        formula=formula,
        requirements=results,
    )


def find_candidate_partial_terms(text: str) -> list[str]:
    """Utility used by tools to keep identifier lookups predictable."""
    return [token for token in re.split(r"\s+", text.strip()) if token]
