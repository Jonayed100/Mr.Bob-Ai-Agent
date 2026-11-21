from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Reminder
from ..timeutil import aware, friendly, now_utc, to_utc
from .activity import record
from .notify import notify
from .reminders import next_due


def serialize(r: Reminder) -> dict:
    due = aware(r.due_at)
    return {
        "id": r.id,
        "text": r.text,
        "notes": r.notes or "",
        "due_at": due.isoformat() if due else None,
        "when": friendly(r.due_at),
        "priority": r.priority or "normal",
        "repeat": r.repeat or "none",
        "done": r.done,
        "overdue": bool(due and not r.done and due < now_utc()),
    }


def fire_due(db: Session) -> list[Reminder]:
    """Send every reminder whose time has come. Repeating ones move to their next time."""
    rows = db.scalars(
        select(Reminder).where(
            Reminder.done.is_(False), Reminder.notified.is_(False), Reminder.due_at.is_not(None),
            Reminder.due_at <= to_utc(now_utc()),
        )
    ).all()
    for r in rows:
        star = "⭐ Important: " if r.priority == "important" else ""
        extra = f"\n{r.notes}" if r.notes else ""
        notify(db, f"🔔 Reminder\n{star}{r.text}{extra}")
        r.notified_at = now_utc()
        r.seen_on_web = False
        record(db, f"Reminded you: {r.text}", "reminder")
        upcoming = next_due(aware(r.due_at), r.repeat or "none")
        if upcoming:
            r.due_at = upcoming  # comes back next time
            r.notified = False
        else:
            r.notified = True
    return rows
