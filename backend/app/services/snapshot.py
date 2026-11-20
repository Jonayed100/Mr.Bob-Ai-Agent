"""Today's data in one place: used by the dashboard, briefings and suggestions."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..integrations import gcalendar, google_auth, weather
from ..models import Alert, Reminder, Suggestion, is_enabled
from ..timeutil import aware, day_bounds, friendly, hhmm

log = logging.getLogger("mrbob")

_weather_cache: dict = {}


def cached_weather() -> dict | None:
    """Weather is refreshed by the hourly job; the dashboard reads this cache."""
    return _weather_cache.get("now")


def refresh_weather() -> dict | None:
    try:
        _weather_cache["now"] = weather.current()
    except Exception as exc:
        log.warning("Weather fetch failed: %s", exc)
    return _weather_cache.get("now")


def events(db: Session, offset_days: int = 0) -> list[dict]:
    if not is_enabled(db, "calendar"):
        return []
    try:
        creds = google_auth.get_credentials(db)
        if not creds:
            return []
        return [
            {
                "title": e["title"],
                "time": "All day" if e["all_day"] else hhmm(e["start"]),
                "where": e["where"],
            }
            for e in gcalendar.events_for_day(creds, offset_days)
        ]
    except Exception as exc:
        log.warning("Calendar read failed: %s", exc)
        return []


def reminders(db: Session) -> list[dict]:
    start, end = day_bounds(0)
    rows = db.scalars(select(Reminder).order_by(Reminder.done, Reminder.due_at)).all()
    out = []
    for r in rows:
        # show open reminders, plus ones finished today
        if r.done and not (r.created_at and start <= aware(r.created_at) < end):
            continue
        out.append({"id": r.id, "text": r.text, "when": friendly(r.due_at), "done": r.done})
    return out[:12]


def alerts(db: Session, limit: int = 8) -> list[dict]:
    rows = db.scalars(select(Alert).where(Alert.score >= 40).order_by(Alert.created_at.desc()).limit(limit)).all()
    return [
        {
            "id": a.id,
            "source": a.source,
            "title": a.title,
            "sender": a.sender,
            "detail": a.detail[:200],
            "level": a.level,
            "reason": a.reason,
            "when": friendly(a.created_at),
        }
        for a in rows
    ]


def suggestions(db: Session) -> list[dict]:
    rows = db.scalars(select(Suggestion).where(Suggestion.active.is_(True)).order_by(Suggestion.id.desc()).limit(4)).all()
    return [{"id": s.id, "text": s.text, "feedback": s.feedback} for s in rows]


def today_snapshot(db: Session) -> dict:
    return {
        "weather": cached_weather() or refresh_weather(),
        "today_events": events(db, 0),
        "tomorrow_events": events(db, 1),
        "reminders": [r for r in reminders(db) if not r["done"]],
        "bkash_this_month": _bkash(db),
        "important_emails": [
            {"from": a["sender"], "subject": a["title"], "why": a["reason"]} for a in alerts(db) if a["source"] == "gmail"
        ],
    }


def _bkash(db: Session) -> dict | None:
    if not is_enabled(db, "bkash"):
        return None
    from .money import month_summary

    s = month_summary(db)
    return {"in": s["in"], "out": s["out"], "balance": s["balance"]} if s["count"] else None
