"""The night briefing: "Hey Mr. Bob, tell me about my important tasks."

Mr. Bob goes through the day part by part (most important first), explains each
one, and saves the whole thing as a report on the website.
"""

import json
import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agent.brain import get_brain
from ..config import get_settings
from ..models import Reminder, Report
from ..timeutil import aware, day_bounds, friendly, now_local, now_utc
from . import memory, snapshot
from .activity import record
from .money import month_summary

log = logging.getLogger("mrbob")

LANG_RULE = {
    "english": "Write everything in clear, natural English.",
    "bangla": "Write everything in natural spoken Bangla, using Bangla script (বাংলা). Keep names and times readable.",
    "banglish": "Write in natural Banglish: Bangla words in English letters, mixed with English the way people in Dhaka talk.",
}

PROMPT = """You are Mr. Bob, {owner}'s personal AI agent: his caring friend and his manager.
It is {now}. He asked you to tell him about his important tasks. Using ONLY the data below, prepare a
spoken briefing that goes part by part.

How to write it:
- Start with the most important and urgent things, then the rest.
- 3 to 7 parts. Each part has a short title and 2 to 4 sentences that EXPLAIN it: what it is, why it
  matters, what exactly to do and by when. Be concrete with times (12-hour format, e.g. 3:00 PM).
- Mark a part "important": true when it is urgent, has a deadline within 24 hours, involves money,
  work/study opportunities, or something he marked important.
- Cover: overdue and today's reminders, tomorrow's schedule and how to prepare, emails that need action,
  money (bKash) if relevant, and one caring personal note using what you remember about him.
- Warm, encouraging, like a good friend who is also a sharp manager. No markdown, no emoji.
- {lang_rule}
- Never invent facts. If something is missing, simply don't mention it.

Reply with JSON only:
{{"title": "...", "summary": "one or two sentences", "parts": [{{"title": "...", "text": "...", "important": true}}],
 "closing": "one short friendly closing line"}}

DATA:
{data}"""


def _language_for(text: str, choice: str) -> str:
    from ..agent.language import detect_style

    if choice in LANG_RULE:
        return choice
    return detect_style(text) if text else "english"


def gather(db: Session) -> dict:
    s = get_settings()
    start, end = day_bounds(0)
    rows = db.scalars(select(Reminder).order_by(Reminder.due_at)).all()
    tomorrow_end = end + timedelta(days=1)
    open_rows = [r for r in rows if not r.done]

    def item(r: Reminder) -> dict:
        return {"text": r.text, "notes": r.notes, "when": friendly(r.due_at) or "no time",
                "important": r.priority == "important", "repeat": r.repeat}

    return {
        "owner": s.owner_name,
        "weather": snapshot.cached_weather() or snapshot.refresh_weather(),
        "today_events": snapshot.events(db, 0),
        "tomorrow_events": snapshot.events(db, 1),
        "overdue_reminders": [item(r) for r in open_rows if r.due_at and aware(r.due_at) < now_utc()],
        "reminders_due_today_or_tomorrow": [item(r) for r in open_rows
                                            if r.due_at and now_utc() <= aware(r.due_at) < tomorrow_end],
        "important_reminders_without_time": [item(r) for r in open_rows if not r.due_at and r.priority == "important"],
        "finished_today": [r.text for r in rows if r.done and r.done_at and start <= aware(r.done_at) < end],
        "important_emails": [{"from": a["sender"], "subject": a["title"], "why": a["reason"]}
                             for a in snapshot.alerts(db) if a["source"] == "gmail" and a["level"] == "high"],
        "bkash_this_month": month_summary(db),
        "what_you_remember_about_him": memory.prompt_block(db, 25),
    }


def _fallback(data: dict, language: str) -> dict:
    """If the AI is unreachable, still give a useful (plainer) briefing."""
    parts = []
    for r in data["overdue_reminders"]:
        parts.append({"title": "Overdue", "text": f"{r['text']} was due {r['when']}. Please do it as soon as you can.", "important": True})
    for r in data["reminders_due_today_or_tomorrow"]:
        parts.append({"title": "Coming up", "text": f"{r['text']}, {r['when']}." + (f" {r['notes']}" if r["notes"] else ""),
                      "important": r["important"]})
    for e in data["tomorrow_events"]:
        parts.append({"title": "Tomorrow", "text": f"{e['title']} at {e['time']}" + (f", {e['where']}." if e["where"] else "."), "important": False})
    for m in data["important_emails"][:3]:
        parts.append({"title": "Email", "text": f"{m['from']} wrote: {m['subject']}.", "important": True})
    if not parts:
        parts.append({"title": "All clear", "text": "Nothing urgent is waiting. Rest well tonight.", "important": False})
    return {"title": f"Report for {now_local():%A, %d %B}", "summary": f"{len(parts)} things to know.",
            "parts": parts[:7], "closing": "Good night, I'll keep watch."}


def build(db: Session, *, said: str = "", language: str = "auto") -> Report:
    s = get_settings()
    lang = _language_for(said, language)
    data = gather(db)
    result = get_brain().complete_json(
        db,
        PROMPT.format(owner=s.owner_name, now=f"{now_local():%A %d %B %Y, %I:%M %p}", lang_rule=LANG_RULE.get(lang, LANG_RULE["english"]),
                      data=json.dumps(data, default=str, ensure_ascii=False)),
        max_tokens=1400,
    )
    if not result.get("parts"):
        result = _fallback(data, lang)
    parts = [
        {"title": str(p.get("title", ""))[:80], "text": str(p.get("text", "")).strip(), "important": bool(p.get("important"))}
        for p in result["parts"] if str(p.get("text", "")).strip()
    ][:8]
    if result.get("closing"):
        parts.append({"title": "Good night", "text": str(result["closing"]), "important": False})
    report = Report(
        day=now_local().strftime("%Y-%m-%d"),
        title=str(result.get("title") or f"Report for {now_local():%A, %d %B}")[:200],
        summary=str(result.get("summary") or "")[:600],
        parts_json=json.dumps(parts, ensure_ascii=False),
        language=lang,
    )
    db.add(report)
    db.flush()
    record(db, f"Saved today's report ({len(parts)} parts)", "report")
    return report


def to_dict(r: Report) -> dict:
    parts = json.loads(r.parts_json or "[]")
    return {
        "id": r.id, "day": r.day, "title": r.title, "summary": r.summary, "language": r.language,
        "parts": parts, "important_count": sum(1 for p in parts if p.get("important")),
        "created": friendly(r.created_at),
    }


def as_text(r: Report) -> str:
    """Plain text for Telegram / WhatsApp."""
    d = to_dict(r)
    lines = [f"📋 {d['title']}", d["summary"], ""]
    for i, p in enumerate(d["parts"], 1):
        lines.append(f"{'⭐ ' if p['important'] else ''}{i}. {p['title']}\n{p['text']}\n")
    return "\n".join(lines).strip()


def spoken(r: Report) -> str:
    d = to_dict(r)
    return " ".join([d["summary"]] + [f"{p['title']}. {p['text']}" for p in d["parts"]])


def nightly(db: Session) -> None:
    """Every night: build the day's report and send it to Telegram / WhatsApp / the phone, with a link."""
    from ..models import kv_get
    from ..voice.tts import speak_sync
    from .notify import notify

    today = now_local().strftime("%Y-%m-%d")
    if db.scalar(select(Report).where(Report.day == today)):
        return  # he already asked for it tonight
    report = build(db, language=kv_get(db, "language", "auto"))
    link = get_settings().public_url.rstrip("/") + "/#reports"
    try:
        voice = speak_sync(spoken(report), report.language)
    except Exception:
        voice = b""
    notify(db, as_text(report) + f"\n\nOpen the full report: {link}", voice=voice, caption="Tonight's report")
