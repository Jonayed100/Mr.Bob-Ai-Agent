"""Free mode: Groq's free model thinks (with tools), so no paid key is needed."""
import json

import pytest

pytest.importorskip("anthropic")
pytest.importorskip("httpx")
pytest.importorskip("sqlalchemy")
pytest.importorskip("pydantic_settings")

import httpx  # noqa: E402

from app.agent import brain as brain_mod  # noqa: E402
from app.config import Settings  # noqa: E402


def test_free_mode_when_no_paid_keys():
    assert Settings(groq_api_key="g", anthropic_api_key="", openai_api_key="").free_mode
    assert not Settings(groq_api_key="g", anthropic_api_key="a").free_mode
    # "groq" forces the free brain even if a Claude key is present
    forced = Settings(anthropic_api_key="a", brain_provider="groq")
    assert not forced.use_claude


def test_tools_are_converted_for_groq():
    names = {t["function"]["name"] for t in brain_mod.GROQ_TOOLS}
    assert {"add_reminder", "remember", "list_reminders"} <= names
    for t in brain_mod.GROQ_TOOLS:
        assert t["type"] == "function" and "properties" in t["function"]["parameters"]


class FakeRunner:
    calls = []

    def __init__(self, db):
        pass

    def run(self, name, args):
        FakeRunner.calls.append((name, args))
        return json.dumps({"ok": True, "when": "Tomorrow 8:00 PM"})


def _response(message, status=200, headers=None):
    req = httpx.Request("POST", brain_mod.GROQ_URL)
    return httpx.Response(status, json={"choices": [{"message": message}]}, headers=headers or {}, request=req)


def _free_brain(monkeypatch, replies):
    monkeypatch.setattr(brain_mod, "ToolRunner", FakeRunner)
    monkeypatch.setattr(brain_mod.memory, "prompt_block", lambda db: "")
    monkeypatch.setattr(brain_mod.time, "sleep", lambda s: None)
    sent = []

    def fake_post(url, headers=None, json=None, timeout=None):
        sent.append(json)
        return replies.pop(0)

    monkeypatch.setattr(brain_mod.httpx, "post", fake_post)
    b = brain_mod.Brain.__new__(brain_mod.Brain)
    b.s = Settings(groq_api_key="test", anthropic_api_key="")
    b.claude = None
    return b, sent


def test_free_brain_uses_tools_then_answers(monkeypatch):
    FakeRunner.calls = []
    tool_call = {"id": "c1", "type": "function",
                 "function": {"name": "add_reminder", "arguments": '{"text": "Call Ammu", "due_at": "2026-11-22T20:00:00"}'}}
    b, sent = _free_brain(monkeypatch, [
        _response({"role": "assistant", "content": "", "tool_calls": [tool_call]}),
        _response({"role": "assistant", "content": "Done! I'll remind you tomorrow at 8:00 PM."}),
    ])
    answer = b._free_chat(None, [], "Remind me to call Ammu tomorrow at 8 PM", "english", False)
    assert answer.startswith("Done!")
    assert FakeRunner.calls == [("add_reminder", {"text": "Call Ammu", "due_at": "2026-11-22T20:00:00"})]
    assert sent[1]["messages"][-1]["role"] == "tool"  # the tool result went back to the model
    assert sent[0]["reasoning_effort"] == "low"


def test_free_brain_waits_once_on_rate_limit(monkeypatch):
    b, sent = _free_brain(monkeypatch, [
        _response({}, status=429, headers={"retry-after": "2"}),
        _response({"role": "assistant", "content": "Hi Jonayed!"}),
    ])
    assert b._free_chat(None, [], "hi", "english", False) == "Hi Jonayed!"
    assert len(sent) == 2


def test_free_brain_explains_when_limit_is_used_up(monkeypatch):
    b, _ = _free_brain(monkeypatch, [
        _response({}, status=429, headers={"retry-after": "60"}),
    ])
    assert "free limit" in b._free_chat(None, [], "hi", "english", False)
