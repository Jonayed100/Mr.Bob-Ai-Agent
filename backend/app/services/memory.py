"""Mr. Bob's long-term memory: what he knows about his owner."""

import json
import logging
import threading

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import session_scope
from ..models import Memory
from .activity import record
from .memory_text import KINDS, is_duplicate, worth_learning_from

log = logging.getLogger("mrbob")

LEARN_PROMPT = """You help a personal assistant remember useful things about its owner, {owner}.
From the message below, pull out durable facts worth remembering for weeks: people in his life,
preferences, goals, routines, important dates, plans, likes and dislikes.
Ignore small talk, one-off questions and anything already obvious. Write each fact as a short
third-person sentence in English (e.g. "His sister Nusrat's birthday is 12 March").
Never store passwords, card or account numbers, OTP codes or ID numbers.
Reply with JSON only: {{"memories": [{{"text": "...", "kind": "fact|preference|person|goal|routine"}}]}}
Return an empty list if there is nothing worth keeping.

MESSAGE:
{message}"""

SENSITIVE = ("password", "otp", "pin ", "card number", "account number", "cvv", "nid")


def all_texts(db: Session) -> list[str]:
    return list(db.scalars(select(Memory.text)))


def add(db: Session, text: str, kind: str = "fact", source: str = "chat") -> Memory | None:
    text = " ".join((text or "").split())[:400]
    if not text or any(w in text.lower() for w in SENSITIVE):
        return None
    if is_duplicate(text, all_texts(db)):
        return None
    m = Memory(text=text, kind=kind if kind in KINDS else "fact", source=source)
    db.add(m)
    db.flush()
    record(db, f"Remembered: {text[:90]}", "memory")
    return m


def prompt_block(db: Session, limit: int = 60) -> str:
    rows = db.scalars(select(Memory).order_by(Memory.id.desc()).limit(limit)).all()
    if not rows:
        return ""
    return "\n".join(f"- {m.text}" for m in reversed(rows))


def learn_in_background(message: str) -> None:
    """After a chat, quietly look for new things to remember (doesn't slow the reply)."""
    if not worth_learning_from(message):
        return

    def run():
        from ..agent.brain import get_brain
        from ..config import get_settings

        try:
            with session_scope() as db:
                result = get_brain().complete_json(
                    db, LEARN_PROMPT.format(owner=get_settings().owner_name, message=message[:1500]), max_tokens=300
                )
                for item in (result.get("memories") or [])[:5]:
                    if isinstance(item, dict):
                        add(db, str(item.get("text", "")), str(item.get("kind", "fact")))
        except Exception as exc:
            log.warning("Memory learning failed: %s", exc)

    threading.Thread(target=run, daemon=True).start()


def to_dict(m: Memory) -> dict:
    return {"id": m.id, "text": m.text, "kind": m.kind, "source": m.source,
            "created": m.created_at.isoformat() if m.created_at else None}


def as_json(db: Session) -> str:
    return json.dumps([to_dict(m) for m in db.scalars(select(Memory).order_by(Memory.id.desc()))], default=str)
