from datetime import datetime

from googleapiclient.discovery import build

from ..timeutil import day_bounds


def _parse(value: dict) -> tuple[datetime | None, bool]:
    """Google gives either dateTime (timed event) or date (all-day)."""
    if "dateTime" in value:
        return datetime.fromisoformat(value["dateTime"].replace("Z", "+00:00")), False
    if "date" in value:
        return datetime.fromisoformat(value["date"]), True
    return None, False


def events_between(creds, start: datetime, end: datetime, limit: int = 20) -> list[dict]:
    svc = build("calendar", "v3", credentials=creds, cache_discovery=False)
    res = (
        svc.events()
        .list(
            calendarId="primary",
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=limit,
        )
        .execute()
    )
    events = []
    for e in res.get("items", []):
        if e.get("status") == "cancelled":
            continue
        starts, all_day = _parse(e.get("start", {}))
        ends, _ = _parse(e.get("end", {}))
        events.append(
            {
                "id": e["id"],
                "title": e.get("summary", "(no title)"),
                "where": e.get("location", "") or ("Online" if e.get("hangoutLink") else ""),
                "start": starts,
                "end": ends,
                "all_day": all_day,
            }
        )
    return events


def events_for_day(creds, offset_days: int = 0) -> list[dict]:
    start, end = day_bounds(offset_days)
    return events_between(creds, start, end)
