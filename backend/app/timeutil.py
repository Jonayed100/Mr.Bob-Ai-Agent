"""Time helpers.

Everything is stored in the database as UTC. SQLite gives naive datetimes
back, so `aware()` treats a naive value as UTC.
"""

from datetime import datetime, timedelta, timezone

from .config import get_settings


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_local() -> datetime:
    return datetime.now(get_settings().tz)


def aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def to_utc(dt: datetime) -> datetime:
    """Convert to UTC. A naive value is taken to be local (Dhaka) time."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=get_settings().tz)
    return dt.astimezone(timezone.utc)


def local(dt: datetime | None) -> datetime | None:
    dt = aware(dt)
    return dt.astimezone(get_settings().tz) if dt else None


def day_bounds(offset_days: int = 0) -> tuple[datetime, datetime]:
    """Start and end of a local day, as aware datetimes."""
    start = now_local().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=offset_days)
    return start, start + timedelta(days=1)


def hhmm(dt: datetime | None) -> str:
    dt = local(dt)
    return dt.strftime("%H:%M") if dt else ""


def friendly(dt: datetime | None) -> str:
    """'Today 15:00', 'Tomorrow 09:30' or '25 Nov 18:00'."""
    dt = local(dt)
    if not dt:
        return ""
    today = now_local().date()
    if dt.date() == today:
        return f"Today {dt:%H:%M}"
    if dt.date() == today + timedelta(days=1):
        return f"Tomorrow {dt:%H:%M}"
    return f"{dt.day} {dt:%b %H:%M}"
