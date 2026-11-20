"""The background checks Mr. Bob runs on a schedule."""

import json
import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agent.brain import get_brain
from ..agent.prompts import IMPORTANCE_PROMPT
from ..config import get_settings
from ..integrations import gcalendar, gmail, google_auth, telegram
from ..models import Alert, Reminder, is_enabled, kv_get, kv_set
from ..timeutil import hhmm, now_local, now_utc, to_utc
from .activity import record
from .importance import clamp, rule_score
from .snapshot import refresh_weather

log = logging.getLogger("mrbob")


def notify(db: Session, text: str) -> None:
    if is_enabled(db, "telegram"):
        try:
            telegram.send_text(text)
        except Exception as exc:
            log.warning("Telegram send failed: %s", exc)


# ---------- Gmail ----------
def check_gmail(db: Session) -> int:
    """Look at new emails, score them, and alert on the important ones. Returns how many were new."""
    if not is_enabled(db, "gmail"):
        return 0
    creds = google_auth.get_credentials(db)
    if not creds:
        return 0
    messages = gmail.recent_messages(creds)
    known = set(db.scalars(select(Alert.external_id).where(Alert.source == "gmail")))
    brain = get_brain()
    new, skipped = 0, 0
    for m in messages:
        ext = f"gmail:{m['id']}"
        if ext in known:
            continue
        new += 1
        score = rule_score(m["from_address"] or m["from"], m["subject"], m["snippet"])
        reason = "matched keywords" if score is not None else ""
        if score is None:
            verdict = brain.complete_json(
                db,
                IMPORTANCE_PROMPT
                + "\n\nEMAIL:\n"
                + json.dumps({"from": m["from"], "subject": m["subject"], "preview": m["snippet"]}, ensure_ascii=False),
                max_tokens=80,
            )
            score = clamp(verdict.get("score", 30)) if verdict else 30
            reason = str(verdict.get("reason", ""))[:300]
        alert = Alert(
            source="gmail",
            external_id=ext,
            title=m["subject"][:300],
            detail=m["snippet"],
            sender=m["from"][:200],
            score=score,
            reason=reason,
        )
        db.add(alert)
        if score >= 70:
            alert.notified = True
            notify(db, f"📩 Important email from {m['from']}\n{m['subject']}")
            record(db, f"Flagged email as important: {m['subject'][:80]}", "gmail")
        elif score < 40:
            skipped += 1
    if new:
        record(db, f"Checked Gmail: {new} new, {skipped} skipped as low priority", "gmail")
    return new


# ---------- Calendar ----------
def calendar_heads_up(db: Session) -> None:
    """Message the user a little before each event starts."""
    if not is_enabled(db, "calendar"):
        return
    creds = google_auth.get_credentials(db)
    if not creds:
        return
    s = get_settings()
    start = now_local()
    soon = start + timedelta(minutes=s.calendar_heads_up_minutes + 5)
    sent = set(json.loads(kv_get(db, "calendar_notified", "[]")))
    for e in gcalendar.events_between(creds, start, soon):
        if e["all_day"] or e["id"] in sent:
            continue
        where = f" at {e['where']}" if e["where"] else ""
        notify(db, f"⏰ Coming up at {hhmm(e['start'])}: {e['title']}{where}")
        record(db, f"Reminded you about {e['title']}", "calendar")
        sent.add(e["id"])
        db.add(Alert(source="calendar", external_id=f"cal:{e['id']}:{e['start']}", title=e["title"],
                     detail=f"Starts {hhmm(e['start'])}{where}", score=60, reason="starting soon"))
    kv_set(db, "calendar_notified", json.dumps(list(sent)[-200:]))


# ---------- Weather ----------
def weather_watch(db: Session) -> None:
    if not is_enabled(db, "weather"):
        return
    w = refresh_weather()
    if not w:
        return
    today = now_local().strftime("%Y-%m-%d")
    if w.get("rain_at"):
        ext = f"rain:{today}"
        if not db.scalar(select(Alert).where(Alert.external_id == ext)):
            db.add(Alert(source="weather", external_id=ext, title=f"Rain likely around {w['rain_at']}",
                         detail=f"{w['condition']}, {w['temp_c']}°C", score=55, reason="take an umbrella"))
            notify(db, f"🌧 Rain likely around {w['rain_at']} in {w['city']}. Take an umbrella.")
            record(db, "Warned you about rain", "weather")
    if (w.get("aqi") or 0) > 150:
        ext = f"aqi:{today}"
        if not db.scalar(select(Alert).where(Alert.external_id == ext)):
            db.add(Alert(source="weather", external_id=ext, title=f"Air quality is {w['aqi_label']} (AQI {w['aqi']})",
                         detail="Wear a mask outside", score=50, reason="health"))
            record(db, "Noted bad air quality", "weather")


# ---------- Reminders ----------
def reminders_due(db: Session) -> None:
    rows = db.scalars(
        select(Reminder).where(
            Reminder.done.is_(False), Reminder.notified.is_(False), Reminder.due_at.is_not(None),
            Reminder.due_at <= to_utc(now_utc()),
        )
    ).all()
    for r in rows:
        notify(db, f"🔔 Reminder: {r.text}")
        r.notified = True
        record(db, f"Sent reminder: {r.text}", "reminder")
