"""Mr. Bob's brain.

Claude does the thinking and can use tools (calendar, email, weather,
reminders). If Claude can't be reached, Groq's free model answers instead
using a snapshot of today's data, so Mr. Bob never goes silent.
"""

import json
import logging
import re

import httpx
from anthropic import Anthropic
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Message
from ..services.costs import add_usage, claude_cost_usd
from .prompts import system_prompt
from .tools import TOOL_SPECS, ToolRunner

log = logging.getLogger("mrbob")
MAX_TOOL_ROUNDS = 6
HISTORY = 10


class Brain:
    def __init__(self):
        self.s = get_settings()
        self.claude = Anthropic(api_key=self.s.anthropic_api_key) if self.s.anthropic_api_key else None

    # ---------- chat ----------
    def reply(self, db: Session, text: str, *, language: str = "auto", channel: str = "web", spoken: bool = False) -> str:
        history = self._history(db)
        db.add(Message(role="user", content=text, channel=channel))
        db.flush()
        try:
            answer = self._claude_chat(db, history + [{"role": "user", "content": text}], language, spoken)
        except Exception as exc:
            log.warning("Claude failed, using backup brain: %s", exc)
            answer = self._backup_chat(db, history, text, language, spoken)
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
        system = system_prompt(language, spoken)
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

    def _backup_chat(self, db: Session, history: list[dict], text: str, language: str, spoken: bool) -> str:
        if not self.s.groq_api_key:
            return "Sorry, my brain is offline right now. Please check the API keys in the settings."
        from ..services.snapshot import today_snapshot  # avoid a circular import

        system = system_prompt(language, spoken) + "\n\nToday's data (you cannot use tools right now):\n" + json.dumps(
            today_snapshot(db), default=str, ensure_ascii=False
        )
        try:
            return self._groq(system, history + [{"role": "user", "content": text}])
        except Exception as exc:
            log.error("Backup brain failed too: %s", exc)
            return "Sorry, I can't think right now. Both my brains are unreachable. Please try again in a minute."

    # ---------- one-shot jobs (importance, suggestions, briefings) ----------
    def complete(self, db: Session, prompt: str, *, max_tokens: int = 400) -> str:
        """A single question with no tools. Claude first, Groq as backup."""
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
            return self._groq("Follow the instructions exactly.", [{"role": "user", "content": prompt}], max_tokens)
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
    def _groq(self, system: str, messages: list[dict], max_tokens: int = 600) -> str:
        r = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.s.groq_api_key}"},
            json={
                "model": self.s.groq_model,
                "messages": [{"role": "system", "content": system}, *messages],
                "max_tokens": max_tokens,
                "temperature": 0.4,
            },
            timeout=45,
        )
        r.raise_for_status()
        return (r.json()["choices"][0]["message"]["content"] or "").strip()

    def _track(self, db: Session, res) -> None:
        usage = getattr(res, "usage", None)
        if usage:
            tokens_in, tokens_out = usage.input_tokens or 0, usage.output_tokens or 0
            add_usage(db, "claude", tokens_in + tokens_out, claude_cost_usd(tokens_in, tokens_out))


def _text_of(res) -> str:
    return "".join(b.text for b in res.content if getattr(b, "type", "") == "text").strip()


_brain: Brain | None = None


def get_brain() -> Brain:
    global _brain
    if _brain is None:
        _brain = Brain()
    return _brain
