"""Generation tools — screening questions and outreach drafts.

Exactly like the agent loop, a provider abstraction decides HOW text is
generated: the deterministic demo generator always works with no API key; the
OpenAI-backed generator uses structured outputs when configured. The grounding
(match result, gaps, strengths) is computed deterministically either way — the
LLM only phrases, it never invents candidates or requirements.
"""

from __future__ import annotations

from app.agent.providers import get_provider
from app.services.matching import MatchResult

_NO_PROTECTED = (
    "Never ask about or allude to protected or personal circumstances "
    "(age, gender, family, nationality, religion, disability, photos)."
)


def _gap_and_strength_lines(match: MatchResult):
    strengths = []
    gaps = []
    for result in match.requirements:
        if result.status == "met" and result.kind == "must_have" and len(strengths) < 3:
            strengths.append(result)
        if result.status in ("partial", "missing") and result.kind == "must_have" and len(gaps) < 2:
            gaps.append(result)
    return strengths, gaps


def _demo_questions(match: MatchResult, count: int) -> list[dict]:
    strengths, gaps = _gap_and_strength_lines(match)
    questions: list[dict] = []
    for result in strengths:
        snippet = result.evidence[0].snippet if result.evidence else None
        if result.category == "experience":
            question = (
                f"You bring {result.label.rstrip('.').lower()} — walk me through the most "
                "complex system you owned end to end."
            )
        elif snippet:
            question = (
                f"Your profile shows “{snippet[:130]}” — walk me through that work end to end. "
                "What did you own, and what was the hardest call you made?"
            )
        else:
            question = (
                f"Walk me through a recent project where you worked with "
                f"{result.label.rstrip('.').lower()}. What did you own end to end?"
            )
        questions.append(
            {
                "question": question,
                "rationale": f"Validates a must-have match: '{result.label[:90]}'.",
                "category": "strength_probe",
            }
        )
    for result in gaps:
        questions.append(
            {
                "question": (
                    f"The role asks for “{result.label[:90]}”. How have you approached that "
                    "area, and what would you want to learn first?"
                ),
                "rationale": f"Honest gap probe: '{result.label[:90]}' is partial/missing.",
                "category": "gap_probe",
            }
        )
    behavioral = [
        {
            "question": "Tell me about a time you disagreed with a technical decision. "
            "How did you handle it?",
            "rationale": "Seniority-calibrated behavioral signal; no personal circumstances.",
            "category": "behavioral",
        },
        {
            "question": "Describe a project you shipped that you would do differently now. "
            "What would you change and why?",
            "rationale": "Reflection and growth signal for the role's seniority.",
            "category": "behavioral",
        },
        {
            "question": f"What interests you about the {match.job_title} role specifically?",
            "rationale": "Role-fit motivation, job-related only.",
            "category": "role_fit",
        },
    ]
    questions.extend(behavioral)
    return questions[:count]


def generate_screening(match: MatchResult, count: int = 6) -> dict:
    provider = get_provider()
    if provider.name == "openai":
        questions = provider.generate_screening_questions(match, count=count)
        return {"generated_by": "openai", "questions": questions}
    return {"generated_by": "demo", "questions": _demo_questions(match, count)}


def _demo_outreach(match: MatchResult) -> dict:
    strengths, gaps = _gap_and_strength_lines(match)
    highlight = strengths[0].label if strengths else None
    highlight_clause = (
        highlight.split("(")[0].strip().rstrip(".").lower() if highlight else None
    )
    lines = [
        f"Hi {match.candidate_name.split()[0]},",
        "",
        f"I'm reaching out about the {match.job_title} role on our team. "
        + (
            f"Your background stood out to us — especially around {highlight_clause}."
            if highlight_clause
            else "Your background stood out to us."
        ),
        "",
        "Would you be open to a short, no-obligation chat this week? Happy to share "
        "more about the team, the product and the process.",
        "",
        "Best,",
        "Nihal — Talent Team",
    ]
    return {
        "generated_by": "demo",
        "subject": f"{match.job_title} — quick intro",
        "body": "\n".join(lines),
    }


def generate_outreach(match: MatchResult) -> dict:
    provider = get_provider()
    if provider.name == "openai":
        draft = provider.draft_outreach(match)
        return {"generated_by": "openai", **draft}
    return _demo_outreach(match)
