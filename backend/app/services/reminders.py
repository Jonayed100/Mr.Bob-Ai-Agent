"""Reminders: firing them on time, repeating them, and showing them."""

import calendar
from datetime import datetime, timedelta

REPEATS = ("none", "daily", "weekly", "monthly")
PRIORITIES = ("normal", "important")


def next_due(due: datetime, repeat: str) -> datetime | None:
    """When a repeating reminder should come back."""
    if repeat == "daily":
        return due + timedelta(days=1)
    if repeat == "weekly":
        return due + timedelta(weeks=1)
    if repeat == "monthly":
        month = due.month % 12 + 1
        year = due.year + (1 if due.month == 12 else 0)
        day = min(due.day, calendar.monthrange(year, month)[1])
        return due.replace(year=year, month=month, day=day)
    return None


def clean_choice(value: str | None, allowed: tuple[str, ...], default: str) -> str:
    value = (value or "").strip().lower()
    return value if value in allowed else default
