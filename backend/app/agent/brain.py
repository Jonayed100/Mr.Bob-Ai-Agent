"""Mr. Bob's brain.

Two brains, both able to use tools (calendar, email, weather, reminders, memory):

* Claude, when ANTHROPIC_API_KEY is set (paid, best quality).
* Groq's free open model, used when there is no Claude key (free mode) or
  when Claude can't be reached, so Mr. Bob never goes silent.
"""

import time

import json
import logging
import re

import httpx
from anthropic import Anthropic
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Message
from ..services import memory
from ..services.costs import add_usage, claude_cost_usd
from .prompts import system_prompt
from .tools import TOOL_SPECS, ToolRunner

log = logging.getLogger("mrbob")
MAX_TOOL_ROUNDS = 6
HISTORY = 10
FREE_HISTORY = 6  # Groq's free plan allows about 8,000 tokens a minute, so keep chats shorter
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# the same tools, in the format Groq (OpenAI-style) expects
GROQ_TOOLS = [
    {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}}
    for t in TOOL_SPECS
]


class Brain:
    def __init__(self):
        self.s = get_settings()
        self.claude = Anthropic(api_key=self.s.anthropic_api_key) if self.s.use_claude else None

    # ---------- chat ----------
    def reply(self, db: Session, text: str, *, language: str = "auto", channel: str = "web", spoken: bool = False) -> str:
        history = self._history(db)
        if not self.claude:
            history = history[-FREE_HISTORY:]
            while history and history[0]["role"] != "user":
                history.pop(0)
        db.add(Message(role="user", content=text, channel=channel))
        db.flush()
        answer = None
        if self.claude:
            try:
                answer = self._claude_chat(db, history + [{"role": "user", "content": text}], language, spoken)
            except Exception as exc:
                log.warning("Claude failed, switching to the free brain: %s", exc)
        if answer is None:
            answer = self._free_chat(db, history, text, language, spoken)
        if answer and not answer.startswith("Sorry,"):
            memory.learn_in_background(text)
        db.add(Message(role="assistant", content=answer, channel=channel))
        return answer

    def _history(self, db: Session) -> list[dict]:
        rows = db.scalars(select(Message).order_by(Message.id.desc()).limit(HISTORY)).all()
        msgs = [{"role": m.role, "content": m.content} for m in reversed(rows)]
        # the Claude API wants the conversation to start with the user
        while msgs and msgs[0]["role"] != "user":
            msgs.pop(0)
        # and roles must alternate; merge any repeats
        merged: list[dict] = []
        for m in msgs:
            if merged and merged[-1]["role"] == m["role"]:
                merged[-1]["content"] += "\n" + m["content"]
            else:
                merged.append(dict(m))
        if merged and merged[-1]["role"] == "user":
            merged.pop()  # the new message is added by the caller
        return merged

    def _claude_chat(self, db: Session, messages: list[dict], language: str, spoken: bool) -> str:
        if not self.claude:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        runner = ToolRunner(db)
        system = system_prompt(language, spoken, memory.prompt_block(db))
        for _ in range(MAX_TOOL_ROUNDS):
            res = self.claude.messages.create(
                model=self.s.claude_model,
                max_tokens=self.s.claude_max_tokens,
                system=system,
                tools=TOOL_SPECS,
                messages=messages,
            )
            self._track(db, res)
            if res.stop_reason != "tool_use":
                return _text_of(res) or "Hmm, I'm not sure. Can you say that another way?"
            messages.append({"role": "assistant", "content": [b.model_dump(exclude_none=True) for b in res.content]})
            results = []
            for block in res.content:
                if block.type == "tool_use":
                    results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": runner.run(block.name, block.input)}
                    )
            messages.append({"role": "user", "content": results})
        return "That took me too many steps. Could you ask in a simpler way?"

    def _free_chat(self, db: Session, history: list[dict], text: str, language: str, spoken: bool) -> str:
        """Groq's free model with the same tools as Claude."""
        if not self.s.groq_api_key:
            return "Sorry, my brain is offline. Add GROQ_API_KEY (free) or ANTHROPIC_API_KEY in the settings."
        runner = ToolRunner(db)
        messages = [
            {"role": "system", "content": system_prompt(language, spoken, memory.prompt_block(db))},
            *history,
            {"role": "user", "content": text},
        ]
        try:
            for _ in range(MAX_TOOL_ROUNDS):
                msg = self._groq_call(self.s.groq_model, messages, tools=GROQ_TOOLS, max_tokens=self.s.claude_max_tokens)
                calls = msg.get("tool_calls") or []
                if not calls:
                    return (msg.get("content") or "").strip() or "Hmm, I'm not sure. Can you say that another way?"
                messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
                for call in calls:
                    fn = call.get("function", {})
                    try:
                        args = json.loads(fn.get("arguments") or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    messages.append({"role": "tool", "tool_call_id": call.get("id"), "content": runner.run(fn.get("name", ""), args)})
            return "That took me too many steps. Could you ask in a simpler way?"
        except RateLimited:
            return "Sorry, I've talked a lot today and hit the free limit. Give me a minute and ask again."
        except Exception as exc:
            log.error("Free brain failed: %s", exc)
            return "Sorry, I can't think right now. Please try again in a minute."

    # ---------- one-shot jobs (importance, suggestions, briefings) ----------
    def complete(self, db: Session, prompt: str, *, max_tokens: int = 400) -> str:
        """A single question with no tools. Claude first, then Groq's small free model."""
        if self.claude:
            try:
                res = self.claude.messages.create(
                    model=self.s.claude_model, max_tokens=max_tokens, messages=[{"role": "user", "content": prompt}]
                )
                self._track(db, res)
                return _text_of(res)
            except Exception as exc:
                log.warning("Claude failed on a background job: %s", exc)
        if self.s.groq_api_key:
            try:
                msg = self._groq_call(
                    self.s.groq_fast_model,
                    [{"role": "system", "content": "Follow the instructions exactly."}, {"role": "user", "content": prompt}],
                    max_tokens=max_tokens + 400,  # room for the model's short reasoning
                )
                return (msg.get("content") or "").strip()
            except Exception as exc:
                log.warning("Free brain failed on a background job: %s", exc)
        return ""

    def complete_json(self, db: Session, prompt: str, *, max_tokens: int = 400) -> dict:
        raw = self.complete(db, prompt, max_tokens=max_tokens)
        match = re.search(r"\{.*\}", raw or "", re.S)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}

    # ---------- helpers ----------
    def _groq_call(self, model: str, messages: list[dict], *, tools: list | None = None, max_tokens: int = 600) -> dict:
        """One request to Groq. Waits briefly and retries once if the free per-minute limit is hit."""
        body = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.4}
        if model.startswith("openai/gpt-oss"):
            body["reasoning_effort"] = "low"  # faster replies and fewer tokens from the free quota
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        for attempt in range(2):
            r = httpx.post(GROQ_URL, headers={"Authorization": f"Bearer {self.s.groq_api_key}"}, json=body, timeout=45)
            if r.status_code == 429:
                wait = _retry_after(r)
                if attempt == 0 and wait <= 12:
                    time.sleep(wait)
                    continue
                raise RateLimited(wait)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]
        raise RateLimited(0)

    def _track(self, db: Session, res) -> None:
        usage = getattr(res, "usage", None)
        if usage:
            tokens_in, tokens_out = usage.input_tokens or 0, usage.output_tokens or 0
            add_usage(db, "claude", tokens_in + tokens_out, claude_cost_usd(tokens_in, tokens_out))


class RateLimited(Exception):
    """Groq's free plan limit was reached for now."""


def _retry_after(r: httpx.Response) -> float:
    try:
        return max(1.0, float(r.headers.get("retry-after", "5")))
    except ValueError:
        return 5.0


def _text_of(res) -> str:
    return "".join(b.text for b in res.content if getattr(b, "type", "") == "text").strip()


_brain: Brain | None = None


def get_brain() -> Brain:
    global _brain
    if _brain is None:
        _brain = Brain()
    return _brain
