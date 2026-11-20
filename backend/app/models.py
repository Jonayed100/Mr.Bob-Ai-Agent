from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, session_scope


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Reminder(Base):
    __tablename__ = "reminders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String(300))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    notified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Alert(Base):
    """Something important Mr. Bob found (an email, an event, the weather)."""

    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(30))  # gmail / calendar / weather
    external_id: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    detail: Mapped[str] = mapped_column(Text, default="")
    sender: Mapped[str] = mapped_column(String(200), default="")
    score: Mapped[int] = mapped_column(Integer, default=0)  # 0..100
    reason: Mapped[str] = mapped_column(String(300), default="")
    notified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    @property
    def level(self) -> str:
        if self.score >= 70:
            return "high"
        if self.score >= 40:
            return "medium"
        return "low"


class Suggestion(Base):
    __tablename__ = "suggestions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String(400))
    feedback: Mapped[str | None] = mapped_column(String(10), nullable=True)  # up / down
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[str] = mapped_column(String(10))  # user / assistant
    content: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(20), default="web")  # web / voice / telegram
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Activity(Base):
    __tablename__ = "activity"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String(300))
    kind: Mapped[str] = mapped_column(String(30), default="info")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Connection(Base):
    __tablename__ = "connections"
    name: Mapped[str] = mapped_column(String(30), primary_key=True)
    label: Mapped[str] = mapped_column(String(60))
    detail: Mapped[str] = mapped_column(String(120), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)


class Usage(Base):
    """Every paid API call, so the dashboard can show real spending."""

    __tablename__ = "usage"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service: Mapped[str] = mapped_column(String(30))  # claude / stt
    units: Mapped[float] = mapped_column(Float, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class KeyValue(Base):
    """Small bits of state: Google token, Telegram offset, etc."""

    __tablename__ = "kv"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


DEFAULT_CONNECTIONS = [
    ("gmail", "Gmail", "Checks new mail regularly", True, 1),
    ("calendar", "Google Calendar", "Today and tomorrow", True, 2),
    ("weather", "Weather", "Rain and air quality", True, 3),
    ("telegram", "Telegram", "Sends you alerts and briefings", True, 4),
]


def seed_connections() -> None:
    with session_scope() as db:
        existing = {c.name for c in db.scalars(select(Connection))}
        for name, label, detail, enabled, sort in DEFAULT_CONNECTIONS:
            if name not in existing:
                db.add(Connection(name=name, label=label, detail=detail, enabled=enabled, sort=sort))


def kv_get(db, key: str, default: str = "") -> str:
    row = db.get(KeyValue, key)
    return row.value if row else default


def kv_set(db, key: str, value: str) -> None:
    row = db.get(KeyValue, key)
    if row:
        row.value = value
    else:
        db.add(KeyValue(key=key, value=value))


def is_enabled(db, name: str) -> bool:
    row = db.get(Connection, name)
    return bool(row and row.enabled)
