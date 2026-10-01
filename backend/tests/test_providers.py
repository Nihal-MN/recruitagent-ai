"""Provider wiring tests — the OpenAI path is stub-tested, never live here.

These tests exercise the exact shapes the OpenAI SDK returns (function_call
items, message items, structured output) with injected fake clients, so the
integration is verified offline. See README for the live-verification status.
"""

from __future__ import annotations

import json

from app.agent.providers.base import AgentState
from app.agent.providers.openai_provider import OpenAIProvider
from app.core.errors import AppError


class FakeFunctionCall:
    def __init__(self, name, arguments, call_id):
        self.type = "function_call"
        self.name = name
        self.arguments = arguments
        self.call_id = call_id


class FakeTextPart:
    def __init__(self, text):
        self.text = text


class FakeMessage:
    def __init__(self, text):
        self.type = "message"
        self.content = [FakeTextPart(text)]


class FakeResponse:
    def __init__(self, output=None, output_text="", output_parsed=None):
        self.output = output or []
        self.output_text = output_text
        self.output_parsed = output_parsed


class FakeResponses:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._next

    def script(self, response):
        self._next = response
        return self


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


def _state(msg="Find candidates."):
    return AgentState(user_message=msg, history=[], observations=[], prior_observations=[])


def test_function_call_becomes_tool_call(monkeypatch):
    client = FakeClient()
    client.responses.script(
        FakeResponse(output=[FakeFunctionCall("search_candidates", '{"query": "amira"}', "call_1")])
    )
    provider = OpenAIProvider(client=client)
    decision = provider.next_step(_state())

    assert decision.tool_call is not None
    assert decision.tool_call.name == "search_candidates"
    assert decision.tool_call.args == {"query": "amira"}
    assert decision.tool_call.ref == "call_1"

    # The request carries the full tool registry (10 tools) and the policy prompt.
    sent = client.responses.calls[0]
    tool_names = {t["name"] for t in sent["tools"]}
    assert tool_names == {
        "search_candidates",
        "get_candidate",
        "search_jobs",
        "get_job",
        "match_candidate",
        "get_pipeline",
        "generate_screening_questions",
        "draft_outreach",
        "update_pipeline",
        "add_candidate_note",
    }
    assert "untrusted" in sent["instructions"].lower()


def test_message_item_becomes_final_answer():
    client = FakeClient()
    client.responses.script(FakeResponse(output=[FakeMessage("Here is the grounded answer.")]))
    provider = OpenAIProvider(client=client)
    decision = provider.next_step(_state())
    assert decision.final_text == "Here is the grounded answer."


def test_functions_outputs_are_paired_by_call_ref():
    client = FakeClient()
    client.responses.script(FakeResponse(output=[FakeMessage("done")]))
    provider = OpenAIProvider(client=client)
    from app.agent.providers.base import Observation

    state = _state()
    state.observations = [
        Observation(
            tool="search_candidates",
            ok=True,
            summary="1 candidate(s) returned",
            data={"candidates": []},
            args={"query": "x"},
            call_ref="call_9",
        )
    ]
    provider.next_step(state)
    sent = client.responses.calls[0]
    kinds = [item.get("type") for item in sent["input"] if isinstance(item, dict)]
    assert "function_call" in kinds and "function_call_output" in kinds
    pair = [item for item in sent["input"] if item.get("type") == "function_call_output"][0]
    assert pair["call_id"] == "call_9"
    assert json.loads(pair["output"])["ok"] is True


def test_structured_generation_parses_output_parsed():
    class Parsed:
        def model_dump(self):
            return {"questions": [{"question": "q", "rationale": "r", "category": "behavioral"}]}

    client = FakeClient()
    client.responses.script(FakeResponse(output_parsed=Parsed()))
    provider = OpenAIProvider(client=client)

    class FakeMatch:
        candidate_name, candidate_id = "A", 1
        job_title, job_id = "J", 2
        score = 50.0
        coverage: dict = {}
        requirements: list = []

    questions = provider.generate_screening_questions(FakeMatch(), count=3)
    assert questions[0]["category"] == "behavioral"


def test_missing_key_raises_provider_unavailable(monkeypatch):
    from app.agent.providers import openai_provider as module

    class NoKeySettings:
        openai_api_key = ""
        resolved_model = "test-model"

    monkeypatch.setattr(module, "get_settings", lambda: NoKeySettings())
    try:
        OpenAIProvider()
        raise AssertionError("expected AppError")
    except AppError as exc:
        assert exc.code.value == "provider_unavailable"


def test_provider_factory_defaults_to_demo_without_key():
    from app.agent.providers import get_provider

    assert get_provider().name == "demo"
