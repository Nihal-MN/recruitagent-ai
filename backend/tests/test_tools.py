"""Tool registry + executor contract tests."""

from __future__ import annotations

from app.tools.executor import execute_tool
from app.tools.registry import REGISTRY, ToolContext
from tests.helpers import amira_and_backend_ids

EXPECTED_TOOLS = {
    "search_candidates": "read",
    "get_candidate": "read",
    "search_jobs": "read",
    "get_job": "read",
    "match_candidate": "read",
    "get_pipeline": "read",
    "generate_screening_questions": "generation",
    "draft_outreach": "generation",
    "update_pipeline": "write",
    "add_candidate_note": "write",
}


def test_registry_contains_exactly_the_ten_contract_tools(db):
    assert set(REGISTRY) == set(EXPECTED_TOOLS)
    for name, kind in EXPECTED_TOOLS.items():
        spec = REGISTRY[name]
        assert spec.kind == kind
        assert spec.description.strip()
        assert spec.input_model.model_json_schema()["type"] == "object"
        assert spec.output_model.model_json_schema()["type"] == "object"


def test_write_tools_require_approval(db):
    for name in ("update_pipeline", "add_candidate_note"):
        assert REGISTRY[name].requires_approval is True
    for name in ("search_candidates", "match_candidate", "draft_outreach"):
        assert REGISTRY[name].requires_approval is False


def test_search_candidates_skill_filter(db):
    outcome = execute_tool(db, "search_candidates", {"skill": "kubernetes", "limit": 10}, ToolContext())
    assert outcome.ok and outcome.result is not None
    names = [c["full_name"] for c in outcome.result["candidates"]]
    assert "Chen Wei" in names and "Mia Chen" in names
    assert all(c["match_score"] is None for c in outcome.result["candidates"])


def test_search_candidates_ranked_by_job(db):
    from sqlalchemy import select

    from app.models import Job

    job = db.scalar(select(Job).where(Job.title == "Senior Backend Engineer"))
    outcome = execute_tool(
        db, "search_candidates", {"job_id": job.id, "limit": 5}, ToolContext()
    )
    assert outcome.ok and outcome.result is not None
    scores = [c["match_score"] for c in outcome.result["candidates"]]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] > 50


def test_get_candidate_by_id_name_and_errors(db):
    amira_id, _ = amira_and_backend_ids(db)
    ok = execute_tool(db, "get_candidate", {"identifier": str(amira_id)}, ToolContext())
    assert ok.ok and ok.result is not None and ok.result["full_name"] == "Amira Haddad"

    missing = execute_tool(db, "get_candidate", {"identifier": "Nobody Here"}, ToolContext())
    assert not missing.ok and missing.error_code == "entity_not_found"

    ambiguous = execute_tool(db, "get_candidate", {"identifier": "Alex"}, ToolContext())
    assert not ambiguous.ok and ambiguous.error_code == "ambiguous_entity"


def test_malformed_arguments_are_rejected(db):
    outcome = execute_tool(db, "search_candidates", {"limit": 999}, ToolContext())
    assert not outcome.ok and outcome.error_code == "validation_error"

    wrong_type = execute_tool(db, "match_candidate", {"candidate_id": "x", "job_id": 1}, ToolContext())
    assert not wrong_type.ok and wrong_type.error_code == "validation_error"


def test_unknown_tool_rejected(db):
    outcome = execute_tool(db, "drop_production_database", {}, ToolContext())
    assert not outcome.ok and outcome.error_code == "validation_error"
    assert "Unknown tool" in (outcome.error_message or "")


def test_match_candidate_contract(db):
    candidate_id, job_id = amira_and_backend_ids(db)
    outcome = execute_tool(
        db, "match_candidate", {"candidate_id": candidate_id, "job_id": job_id}, ToolContext()
    )
    assert outcome.ok and outcome.result is not None
    result = outcome.result
    for key in ("score", "formula", "components", "coverage", "requirements", "engine_version"):
        assert key in result
    assert result["requirements"], "requirements must be included for grounding"


def test_generation_contracts(db):
    candidate_id, job_id = amira_and_backend_ids(db)
    screening = execute_tool(
        db,
        "generate_screening_questions",
        {"candidate_id": candidate_id, "job_id": job_id, "count": 5},
        ToolContext(),
    )
    assert screening.ok and screening.result is not None
    questions = screening.result["questions"]
    assert 0 < len(questions) <= 5
    allowed = {"strength_probe", "gap_probe", "behavioral", "role_fit"}
    assert all(q["category"] in allowed for q in questions)
    assert all(q["rationale"] for q in questions)

    outreach = execute_tool(
        db, "draft_outreach", {"candidate_id": candidate_id, "job_id": job_id}, ToolContext()
    )
    assert outreach.ok and outreach.result is not None
    assert outreach.result["subject"] and outreach.result["body"]


def test_get_pipeline_contract(db):
    outcome = execute_tool(db, "get_pipeline", {}, ToolContext())
    assert outcome.ok and outcome.result is not None
    assert outcome.result["total"] >= 10
    assert set(outcome.result["columns"]).issuperset({"NEW", "SCREENING", "INTERVIEW"})
