"""API surface tests — conversations, approvals, trace, activity, directory."""

from __future__ import annotations


def test_health_reports_modes_and_counts(client):
    payload = client.get("/api/v1/health").json()
    assert payload["status"] == "ok"
    assert payload["database"]["status"] == "ok"
    assert payload["ai"]["provider"] == "demo"  # keyless environment
    assert payload["ai"]["api_key_configured"] is False
    assert payload["counts"]["candidates"] == 20
    assert payload["counts"]["jobs"] == 5


def test_full_agent_flow_over_api(client):
    cid = client.post("/api/v1/conversations", json={}).json()["id"]

    turn1 = client.post(
        f"/api/v1/conversations/{cid}/messages",
        json={"content": "Find candidates for the Senior Backend Engineer role."},
    )
    assert turn1.status_code == 200
    body = turn1.json()
    assert body["stopped_reason"] == "final"
    assert len(body["tool_execution_ids"]) >= 2
    assert "Amira Haddad" in body["final_text"]

    turn2 = client.post(
        f"/api/v1/conversations/{cid}/messages",
        json={"content": "Move this candidate to INTERVIEW."},
    )
    approval_ids = turn2.json()["approval_ids"]
    assert approval_ids, "move must create an approval"

    pending = client.get("/api/v1/approvals?status=PENDING").json()
    assert any(a["id"] == approval_ids[0] for a in pending)

    approved = client.post(
        f"/api/v1/approvals/{approval_ids[0]}/approve", json={"decided_by": "api-test"}
    ).json()
    assert approved["status"] == "EXECUTED"
    assert "moved" in (approved["result_summary"] or "")

    # replay via API — no double execution
    again = client.post(
        f"/api/v1/approvals/{approval_ids[0]}/approve", json={"decided_by": "api-test"}
    ).json()
    assert again["status"] == "EXECUTED"

    detail = client.get(f"/api/v1/conversations/{cid}").json()
    assert [m["role"] for m in detail["messages"]][:2] == ["user", "assistant"]
    statuses = [e["status"] for e in detail["tool_executions"]]
    assert "AWAITING_APPROVAL" in statuses

    activity = client.get("/api/v1/activity?limit=20").json()
    types = [e["type"] for e in activity]
    for expected in ("conversation_started", "approval_requested", "approval_approved", "stage_moved"):
        assert expected in types


def test_reject_over_api_causes_zero_mutation(client):
    cid = client.post("/api/v1/conversations", json={}).json()["id"]
    client.post(
        f"/api/v1/conversations/{cid}/messages",
        json={"content": "Find candidates for the Senior Backend Engineer role."},
    )
    turn = client.post(
        f"/api/v1/conversations/{cid}/messages",
        json={"content": "Move this candidate to OFFER."},
    ).json()
    aid = turn["approval_ids"][0]

    before = client.get("/api/v1/pipeline").json()
    rejected = client.post(f"/api/v1/approvals/{aid}/reject", json={}).json()
    assert rejected["status"] == "REJECTED"
    after = client.get("/api/v1/pipeline").json()
    assert before == after


def test_error_shapes_and_404s(client):
    missing = client.get("/api/v1/conversations/9999")
    assert missing.status_code == 404

    bad = client.post("/api/v1/conversations/9999/messages", json={"content": "hi"})
    assert bad.status_code == 404

    validation = client.post("/api/v1/conversations/1/messages", json={"content": ""})
    assert validation.status_code == 422  # pydantic request validation


def test_directory_endpoints(client):
    cands = client.get("/api/v1/candidates?limit=5")
    assert cands.status_code == 200
    assert cands.headers.get("x-total-count") == "20"
    assert len(cands.json()) <= 5

    one = client.get("/api/v1/candidates/1").json()
    assert one["full_name"] and "skills" in one and "notes" in one

    jobs = client.get("/api/v1/jobs").json()
    assert len(jobs) == 5

    detail = client.get("/api/v1/jobs/1").json()
    assert detail["requirements"]

    pipeline = client.get("/api/v1/pipeline").json()
    assert pipeline["total"] >= 10

    # The tool trace is populated by real turns, not prefabricated fixtures.
    cid = client.post("/api/v1/conversations", json={}).json()["id"]
    client.post(
        f"/api/v1/conversations/{cid}/messages",
        json={"content": "Find candidates for the Senior Backend Engineer role."},
    )
    trace = client.get("/api/v1/tool-executions?limit=10").json()
    assert trace and all("tool_name" in e for e in trace)


def test_ambiguous_and_missing_lookups_surface_clean_messages(client):
    cid = client.post("/api/v1/conversations", json={}).json()["id"]
    ambiguous = client.post(
        f"/api/v1/conversations/{cid}/messages", json={"content": "Please show me Alex"}
    ).json()
    assert "ambiguous" in ambiguous["final_text"].lower()

    missing = client.post(
        f"/api/v1/conversations/{cid}/messages",
        json={"content": "Find candidates for the Chief Astronaut role."},
    ).json()
    assert "couldn't find" in missing["final_text"].lower()
