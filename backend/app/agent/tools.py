"""The tools Claude can use, and the code that runs them."""

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..integrations import gcalendar, gmail, google_auth, weather
from ..models import Alert, Reminder, is_enabled
from ..services.activity import record
from ..services.reminders import PRIORITIES, REPEATS, clean_choice
from ..timeutil import friendly, hhmm, now_utc, to_utc

TOOL_SPECS = [
    {
        "name": "get_schedule",
        "description": "Get the user's Google Calendar events for today or tomorrow.",
        "input_schema": {
            "type": "object",
            "properties": {"day": {"type": "string", "enum": ["today", "tomorrow"]}},
            "required": ["day"],
        },
    },
    {
        "name": "get_important_emails",
        "description": "Get the recent emails Mr. Bob marked as important or worth a look, newest first.",
        "input_schema": {"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 15}}},
    },
    {
        "name": "search_emails",
        "description": "Search the user's Gmail (Gmail search syntax, e.g. 'from:desco newer_than:30d').",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    },
    {
        "name": "get_weather",
        "description": "Current weather, rain later today and air quality for the user's city.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_reminders",
        "description": "List the user's open reminders.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "add_reminder",
        "description": "Create a reminder or task. At the due time Mr. Bob alerts the user on the website, Telegram, WhatsApp and the phone app.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "What to remind about, short."},
                "due_at": {"type": "string", "description": "ISO 8601 date-time with timezone offset, or empty if no time."},
                "priority": {"type": "string", "enum": ["normal", "important"]},
                "repeat": {"type": "string", "enum": ["none", "daily", "weekly", "monthly"]},
                "notes": {"type": "string", "description": "Optional details."},
            },
            "required": ["text"],
        },
    },
    {
        "name": "update_reminder",
        "description": "Change a reminder's text, time, priority, repeat or notes (get the id from list_reminders).",
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "text": {"type": "string"},
                "due_at": {"type": "string"},
                "priority": {"type": "string", "enum": ["normal", "important"]},
                "repeat": {"type": "string", "enum": ["none", "daily", "weekly", "monthly"]},
                "notes": {"type": "string"},
            },
            "required": ["id"],
        },
    },
    {
        "name": "delete_reminder",
        "description": "Delete a reminder.",
        "input_schema": {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]},
    },
    {
        "name": "remember",
        "description": "Save something about the user to long-term memory (people, dates, preferences, goals, routines).",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Short third-person sentence, e.g. 'His sister's birthday is 12 March'."},
                "kind": {"type": "string", "enum": ["fact", "preference", "person", "goal", "routine"]},
            },
            "required": ["text"],
        },
    },
    {
        "name": "forget",
        "description": "Delete something from memory (get the id from list_memories).",
        "input_schema": {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]},
    },
    {
        "name": "list_memories",
        "description": "Everything Mr. Bob remembers about the user, with ids.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "complete_reminder",
        "description": "Mark a reminder as done.",
        "input_schema": {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]},
    },
    {
        "name": "get_bkash_summary",
        "description": "This month's bKash money in and out, fees, current balance and recent transactions.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "create_email_draft",
        "description": "Save an email draft in Gmail for the user to review and send himself. Never sends.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["to", "subject", "body"],
        },
    },
]


class ToolRunner:
    def __init__(self, db: Session):
        self.db = db

    def run(self, name: str, args: dict) -> str:
        fn = getattr(self, f"_{name}", None)
        if not fn:
            return json.dumps({"error": f"unknown tool {name}"})
        try:
            return json.dumps(fn(**(args or {})), default=str, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"error": str(exc)[:300]})

    def _creds(self, connection: str):
        if not is_enabled(self.db, connection):
            raise RuntimeError(f"{connection} is switched off on the dashboard")
        creds = google_auth.get_credentials(self.db)
        if not creds:
            raise RuntimeError("Google is not connected yet. Connect it from the dashboard settings.")
        return creds

    def _get_schedule(self, day: str = "today"):
        events = gcalendar.events_for_day(self._creds("calendar"), 1 if day == "tomorrow" else 0)
        record(self.db, f"Checked Calendar ({day})", "calendar")
        return [
            {"title": e["title"], "time": "all day" if e["all_day"] else hhmm(e["start"]), "where": e["where"]}
            for e in events
        ]

    def _get_important_emails(self, limit: int = 8):
        rows = self.db.scalars(
            select(Alert).where(Alert.source == "gmail", Alert.score >= 40).order_by(Alert.created_at.desc()).limit(limit)
        ).all()
        record(self.db, "Looked through important emails", "gmail")
        return [
            {"from": a.sender, "subject": a.title, "preview": a.detail[:200], "importance": a.level, "why": a.reason}
            for a in rows
        ]

    def _search_emails(self, query: str):
        found = gmail.recent_messages(self._creds("gmail"), query=query, limit=8)
        record(self.db, f"Searched Gmail: {query}", "gmail")
        return [{"from": m["from"], "subject": m["subject"], "date": m["date"], "preview": m["snippet"]} for m in found]

    def _get_weather(self):
        if not is_enabled(self.db, "weather"):
            raise RuntimeError("weather is switched off on the dashboard")
        record(self.db, "Checked the weather", "weather")
        return weather.current()

    def _list_reminders(self):
        rows = self.db.scalars(select(Reminder).where(Reminder.done.is_(False)).order_by(Reminder.due_at)).all()
        return [{"id": r.id, "text": r.text, "when": friendly(r.due_at) or "no time", "priority": r.priority,
                 "repeat": r.repeat, "notes": r.notes} for r in rows]

    def _add_reminder(self, text: str, due_at: str = "", priority: str = "normal", repeat: str = "none", notes: str = ""):
        when = to_utc(datetime.fromisoformat(due_at)) if due_at else None
        r = Reminder(text=text[:300], due_at=when, notes=(notes or "")[:1000],
                     priority=clean_choice(priority, PRIORITIES, "normal"), repeat=clean_choice(repeat, REPEATS, "none"))
        self.db.add(r)
        self.db.flush()
        record(self.db, f"Added reminder: {text}" + (f" ({friendly(when)})" if when else ""), "reminder")
        return {"ok": True, "id": r.id, "when": friendly(when) or "no time"}

    def _update_reminder(self, id: int, text: str | None = None, due_at: str | None = None, priority: str | None = None,
                         repeat: str | None = None, notes: str | None = None):
        r = self.db.get(Reminder, id)
        if not r:
            return {"ok": False, "error": "no such reminder"}
        if text:
            r.text = text[:300]
        if due_at is not None:
            r.due_at = to_utc(datetime.fromisoformat(due_at)) if due_at else None
            r.notified = False
        if priority:
            r.priority = clean_choice(priority, PRIORITIES, r.priority)
        if repeat:
            r.repeat = clean_choice(repeat, REPEATS, r.repeat)
        if notes is not None:
            r.notes = notes[:1000]
        record(self.db, f"Updated reminder: {r.text}", "reminder")
        return {"ok": True, "when": friendly(r.due_at) or "no time"}

    def _delete_reminder(self, id: int):
        r = self.db.get(Reminder, id)
        if not r:
            return {"ok": False, "error": "no such reminder"}
        self.db.delete(r)
        record(self.db, f"Deleted reminder: {r.text}", "reminder")
        return {"ok": True}

    def _remember(self, text: str, kind: str = "fact"):
        from ..services import memory

        m = memory.add(self.db, text, kind, source="chat")
        return {"ok": True, "saved": bool(m)}

    def _forget(self, id: int):
        from ..models import Memory

        m = self.db.get(Memory, id)
        if not m:
            return {"ok": False, "error": "no such memory"}
        self.db.delete(m)
        record(self.db, f"Forgot: {m.text[:80]}", "memory")
        return {"ok": True}

    def _list_memories(self):
        from ..models import Memory

        return [{"id": m.id, "text": m.text, "kind": m.kind} for m in self.db.scalars(select(Memory).order_by(Memory.id))]

    def _complete_reminder(self, id: int):
        r = self.db.get(Reminder, id)
        if not r:
            return {"ok": False, "error": "no such reminder"}
        r.done = True
        r.done_at = now_utc()
        record(self.db, f"Completed: {r.text}", "reminder")
        return {"ok": True}

    def _get_bkash_summary(self):
        from ..services.money import month_summary

        if not is_enabled(self.db, "bkash"):
            raise RuntimeError("bKash tracking is switched off on the dashboard")
        record(self.db, "Checked your bKash", "bkash")
        return month_summary(self.db)

    def _create_email_draft(self, to: str, subject: str, body: str):
        draft_id = gmail.create_draft(self._creds("gmail"), to, subject, body)
        record(self.db, f"Saved a Gmail draft to {to}", "gmail")
        return {"ok": True, "draft_id": draft_id, "note": "Saved as a draft. The user must review and send it."}
