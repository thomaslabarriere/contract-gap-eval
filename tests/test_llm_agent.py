"""LLM path, tested with a stubbed client (no network, no API credits).

Proves the code that actually ships and breaks in production: tool-call
parsing (valid AND malformed), the success mapping, and the fail-safe path
(an API error must never be read as 'compliant' or 'gap').
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from contractgap import llm_agent
from contractgap.contracts import get_contract
from contractgap.llm_agent import LLMAgent, _parse
from contractgap.models import GapStatus
from contractgap.policy import get_rule


def _fake_client(create_fn: Any) -> Any:
    """A stand-in for openai.OpenAI exposing chat.completions.create."""
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create_fn)))


def _tool_completion(args: dict[str, Any]) -> Any:
    call = SimpleNamespace(
        type="function",
        id="call_1",
        function=SimpleNamespace(name="report_gap", arguments=json.dumps(args)),
    )
    message = SimpleNamespace(tool_calls=[call], content=None)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message)],
        usage=SimpleNamespace(prompt_tokens=11, completion_tokens=4),
    )


# --- Pure parser: robust to valid and malformed tool-call payloads ----------

def test_parse_accepts_a_valid_payload() -> None:
    v = _parse("LIAB-CAP", '{"status": "gap", "evidence": "clause X", "explanation": "y"}')
    assert v is not None
    assert v.status is GapStatus.GAP
    assert v.evidence == "clause X"


def test_parse_rejects_malformed_payloads() -> None:
    assert _parse("LIAB-CAP", "not json at all") is None          # invalid JSON
    assert _parse("LIAB-CAP", '["a", "b"]') is None               # not an object
    assert _parse("LIAB-CAP", '{"status": "bogus"}') is None      # invalid enum
    assert _parse("LIAB-CAP", '{"explanation": "x"}') is None     # missing status


def test_parse_drops_empty_or_nonstring_evidence() -> None:
    v = _parse("LIAB-CAP", '{"status": "compliant", "evidence": "", "explanation": "y"}')
    assert v is not None and v.evidence is None


# --- LLMAgent.run over the stubbed client -----------------------------------

def test_llm_agent_maps_a_toolcall_to_a_verdict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        llm_agent,
        "make_client",
        lambda *a, **k: _fake_client(
            lambda **kw: _tool_completion(
                {"status": "gap", "evidence": "Responsabilité illimitée", "explanation": "e"}
            )
        ),
    )
    agent = LLMAgent(model="gpt-4o")
    verdict, usage = agent.run(get_contract("C-2"), get_rule("LIAB-CAP"))
    assert verdict.status is GapStatus.GAP
    assert usage.prompt_tokens == 11 and usage.completion_tokens == 4


def test_llm_agent_fails_safe_on_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(**kw: Any) -> Any:
        raise RuntimeError("API is down")

    monkeypatch.setattr(llm_agent, "make_client", lambda *a, **k: _fake_client(boom))
    agent = LLMAgent(model="gpt-4o")
    verdict, _ = agent.run(get_contract("C-2"), get_rule("LIAB-CAP"))
    # A failed call must never be read as compliant or as a gap.
    assert verdict.status is GapStatus.NOT_APPLICABLE
    assert "erreur" in verdict.explanation.lower()


def test_llm_agent_is_undecided_when_no_toolcall(monkeypatch: pytest.MonkeyPatch) -> None:
    empty = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[], content=None))],
        usage=SimpleNamespace(prompt_tokens=5, completion_tokens=0),
    )
    monkeypatch.setattr(
        llm_agent, "make_client", lambda *a, **k: _fake_client(lambda **kw: empty)
    )
    agent = LLMAgent(model="gpt-4o")
    verdict, _ = agent.run(get_contract("C-2"), get_rule("LIAB-CAP"))
    assert verdict.status is GapStatus.NOT_APPLICABLE
