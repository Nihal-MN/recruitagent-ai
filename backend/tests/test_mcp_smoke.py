"""MCP smoke test — launches the real stdio server and calls real tools.

This is the honest end-to-end check: a subprocess MCP server over a file-backed
SQLite database, driven by the official MCP client. It verifies:

- the server starts and lists the documented tools,
- a read tool returns grounded data,
- invalid arguments are rejected (isError),
- propose_pipeline_update creates a PENDING approval and mutates nothing.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _prepare_database(tmp_path: Path) -> str:
    """Create + seed a file-backed SQLite DB the subprocess can open too."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.models  # noqa: F401  (register all tables)
    from app.db.base import Base
    from app.seed import run_seed

    url = f"sqlite:///{tmp_path / 'mcp-smoke.db'}"
    engine = create_engine(url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        run_seed.seed(session)
    return url


def _flag_error(result) -> bool:
    """MCP SDK naming differs across versions (isError / is_error)."""
    for attr in ("isError", "is_error"):
        value = getattr(result, attr, None)
        if value is not None:
            return bool(value)
    for item in getattr(result, "content", []) or []:
        text = (getattr(item, "text", "") or "")
        if text.startswith("Error") or "validation_error" in text:
            return True
    return False


def _payload(result) -> dict:
    structured = getattr(result, "structuredContent", None)
    if structured:
        return structured
    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                continue
    return {}


async def _run_smoke(db_url: str) -> dict:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp_server"],
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "DATABASE_URL": db_url,
            "AI_PROVIDER": "mock",
            "OPENAI_API_KEY": "",
            "PYTHONUNBUFFERED": "1",
            "HOME": str(BACKEND_DIR),
        },
        cwd=str(BACKEND_DIR),
    )
    results: dict = {}

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            results["tool_names"] = sorted(t.name for t in tools.tools)

            found = await session.call_tool("search_candidates", {"skill": "kubernetes"})
            results["search"] = _payload(found)
            results["search_is_error"] = _flag_error(found)

            job = await session.call_tool("search_jobs", {"query": "Senior Backend"})
            job_payload = _payload(job)
            results["job"] = job_payload

            match = await session.call_tool(
                "match_candidate", {"candidate_id": 1, "job_id": 1}
            )
            results["match"] = _payload(match)

            bad = await session.call_tool("search_candidates", {"limit": 999})
            results["invalid_is_error"] = _flag_error(bad)

            proposal = await session.call_tool(
                "propose_pipeline_update",
                {"candidate_id": 1, "job_id": 1, "to_stage": "INTERVIEW"},
            )
            results["proposal"] = _payload(proposal)

    return results


def test_mcp_server_smoke(tmp_path: Path):
    db_url = _prepare_database(tmp_path)
    results = asyncio.run(_run_smoke(db_url))

    assert set(results["tool_names"]) == {
        "search_candidates",
        "get_candidate",
        "search_jobs",
        "get_job",
        "match_candidate",
        "get_pipeline",
        "propose_pipeline_update",
    }

    assert not results["search_is_error"]
    names = [c["full_name"] for c in results["search"]["candidates"]]
    assert "Chen Wei" in names and "Mia Chen" in names

    assert results["job"]["count"] >= 1
    assert results["match"]["score"] > 0
    assert results["match"]["requirements"]

    assert results["invalid_is_error"], "over-limit argument must be rejected"

    proposal = results["proposal"]
    assert proposal["status"] == "PENDING"
    assert proposal["approval_id"] > 0

    # The proposal must NOT have changed anything — verify against the DB file.
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker

    from app.models import Application, ApprovalRequest, ApprovalStatus

    engine = create_engine(db_url)
    with sessionmaker(bind=engine)() as session:
        request = session.get(ApprovalRequest, proposal["approval_id"])
        assert request is not None and request.status == ApprovalStatus.PENDING
        application = session.scalar(
            select(Application).where(Application.candidate_id == 1, Application.job_id == 1)
        )
        assert application is not None and application.stage == "SCREENING"


if __name__ == "__main__":  # pragma: no cover - manual run support
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        url = _prepare_database(Path(tmp))
        print(json.dumps(asyncio.run(_run_smoke(url)), indent=2, default=str))
        pytest.skip("manual smoke run complete")
