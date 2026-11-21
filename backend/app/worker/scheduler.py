"""Everything Mr. Bob does on his own, on a timer."""

import logging
from datetime import datetime

import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from ..config import get_settings
from ..db import session_scope
from ..services import briefing, checks, debrief

log = logging.getLogger("mrbob")


def _safe(name: str, fn, *args):
    """Run one job in its own database session; never let one failure stop the others."""

    def job():
        try:
            with session_scope() as db:
                fn(db, *args)
        except Exception:
            log.exception("Job '%s' failed", name)

    job.__name__ = name
    return job


def _at(hhmm: str) -> CronTrigger:
    hour, minute = (int(x) for x in hhmm.split(":"))
    return CronTrigger(hour=hour, minute=minute, timezone=get_settings().timezone)


def _keep_awake() -> None:
    """Visit our own public address so a free host doesn't put Mr. Bob to sleep."""
    url = get_settings().public_url.rstrip("/") + "/health"
    try:
        httpx.get(url, timeout=20)
    except Exception as exc:
        log.warning("Keep-awake ping failed: %s", exc)


def start() -> BackgroundScheduler:
    s = get_settings()
    sched = BackgroundScheduler(timezone=s.timezone, job_defaults={"coalesce": True, "max_instances": 1})
    first = datetime.now(s.tz)  # run the quick checks right away so the dashboard isn't empty
    sched.add_job(_safe("gmail", checks.check_gmail), "interval", minutes=s.gmail_check_minutes, id="gmail",
                  next_run_time=first)
    sched.add_job(_safe("calendar", checks.calendar_heads_up), "interval", minutes=5, id="calendar")
    sched.add_job(_safe("weather", checks.weather_watch), "interval", hours=1, id="weather", next_run_time=first)
    sched.add_job(_safe("reminders", checks.reminders_due), "interval", seconds=30, id="reminders")
    sched.add_job(_safe("suggestions", briefing.refresh_suggestions), CronTrigger(hour="8-22/3", minute=5,
                  timezone=s.timezone), id="suggestions")
    sched.add_job(_safe("morning", briefing.send_briefing, "morning"), _at(s.morning_briefing_time), id="morning")
    # the night report replaces the old evening summary
    sched.add_job(_safe("night_report", debrief.nightly), _at(s.evening_summary_time), id="night_report")
    if s.keep_awake and s.public_url.startswith("https://"):
        sched.add_job(_keep_awake, "interval", minutes=10, id="keep_awake")
        log.info("Keep-awake is on: pinging %s/health every 10 minutes", s.public_url.rstrip("/"))
    sched.start()
    log.info("Scheduler started")
    return sched
