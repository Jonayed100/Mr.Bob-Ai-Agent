import base64
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from .agent.brain import get_brain
from .config import Settings, get_settings
from .db import get_db
from .integrations import google_auth
from .models import Activity, Connection, Message, Reminder, Suggestion, kv_get, kv_set
from .security import COOKIE, MAX_AGE, make_token, password_ok, require_login
from .services import briefing, costs, snapshot
from .services.activity import record
from .timeutil import friendly, hhmm, now_local, to_utc
from .voice import stt, tts

router = APIRouter(prefix="/api")
auth = [Depends(require_login)]
LANGS = {"auto", "english", "bangla", "banglish"}


# ---------- login ----------
class LoginIn(BaseModel):
    password: str


@router.post("/login")
def login(body: LoginIn, response: Response, settings: Settings = Depends(get_settings)):
    if not password_ok(body.password, settings):
        raise HTTPException(401, "Wrong password")
    response.set_cookie(
        COOKIE, make_token(settings), max_age=MAX_AGE, httponly=True, samesite="lax",
        secure=settings.public_url.startswith("https://"),
    )
    return {"ok": True}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE)
    return {"ok": True}


@router.get("/me", dependencies=auth)
def me(settings: Settings = Depends(get_settings)):
    return {"owner": settings.owner_name, "city": settings.city}


# ---------- dashboard ----------
@router.get("/dashboard", dependencies=auth)
def dashboard(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    now = now_local()
    conns = db.scalars(select(Connection).order_by(Connection.sort)).all()
    google = google_auth.is_connected(db)
    activity = db.scalars(select(Activity).order_by(Activity.id.desc()).limit(25)).all()
    return {
        "owner": settings.owner_name,
        "now": {"day": now.strftime("%A").upper(), "date": now.day, "time": now.strftime("%H:%M")},
        "weather": snapshot.cached_weather() or snapshot.refresh_weather(),
        "events": snapshot.events(db, 0),
        "reminders": snapshot.reminders(db),
        "alerts": snapshot.alerts(db),
        "suggestions": snapshot.suggestions(db),
        "connections": [
            {
                "name": c.name,
                "label": c.label,
                "detail": c.detail if (c.name not in ("gmail", "calendar") or google) else "Not connected yet",
                "enabled": c.enabled,
            }
            for c in conns
        ],
        "google": {"ready": settings.google_ready, "connected": google},
        "telegram": {"ready": settings.telegram_ready, "chat_set": bool(settings.telegram_chat_id)},
        "activity": [{"time": hhmm(a.created_at), "text": a.text} for a in activity],
        "cost": costs.month_summary(db),
        "language": kv_get(db, "language", "auto"),
        "brain": {"claude": bool(settings.anthropic_api_key), "backup": bool(settings.groq_api_key)},
    }


# ---------- talking ----------
class ChatIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    language: str = "auto"
    speak: bool = False


def _lang(db: Session, given: str) -> str:
    language = given.lower() if given and given.lower() in LANGS else "auto"
    if language != kv_get(db, "language", "auto"):
        kv_set(db, "language", language)
    return language


@router.post("/chat", dependencies=auth)
async def chat(body: ChatIn, db: Session = Depends(get_db)):
    language = _lang(db, body.language)
    answer = await run_in_threadpool(
        get_brain().reply, db, body.text.strip(), language=language, channel="web", spoken=body.speak
    )
    db.commit()
    audio = await tts.speak(answer, language) if body.speak else b""
    return {"reply": answer, "audio": base64.b64encode(audio).decode() if audio else None}


@router.post("/voice", dependencies=auth)
async def voice(
    audio: UploadFile = File(...),
    seconds: float = Form(0),
    language: str = Form("auto"),
    db: Session = Depends(get_db),
):
    data = await audio.read()
    if len(data) < 800:
        raise HTTPException(400, "That recording was too short")
    language = _lang(db, language)
    heard = await run_in_threadpool(stt.transcribe, db, data, audio.filename or "voice.webm", seconds)
    if not heard:
        db.commit()
        return {"heard": "", "reply": "Sorry, I couldn't hear that. Try again?", "audio": None}
    answer = await run_in_threadpool(get_brain().reply, db, heard, language=language, channel="voice", spoken=True)
    db.commit()
    mp3 = await tts.speak(answer, language)
    return {"heard": heard, "reply": answer, "audio": base64.b64encode(mp3).decode() if mp3 else None}


@router.get("/messages", dependencies=auth)
def messages(db: Session = Depends(get_db)):
    rows = db.scalars(select(Message).order_by(Message.id.desc()).limit(30)).all()
    return [{"role": m.role, "text": m.content, "channel": m.channel} for m in reversed(rows)]


# ---------- reminders, suggestions, connections ----------
class ReminderIn(BaseModel):
    text: str = Field(min_length=1, max_length=300)
    due_at: datetime | None = None


@router.post("/reminders", dependencies=auth)
def add_reminder(body: ReminderIn, db: Session = Depends(get_db)):
    r = Reminder(text=body.text, due_at=to_utc(body.due_at) if body.due_at else None)
    db.add(r)
    record(db, f"Added reminder: {body.text}" + (f" ({friendly(r.due_at)})" if r.due_at else ""), "reminder")
    db.commit()
    return {"id": r.id}


class DoneIn(BaseModel):
    done: bool


@router.patch("/reminders/{rid}", dependencies=auth)
def set_reminder(rid: int, body: DoneIn, db: Session = Depends(get_db)):
    r = db.get(Reminder, rid)
    if not r:
        raise HTTPException(404, "Not found")
    r.done = body.done
    if body.done:
        record(db, f"Completed: {r.text}", "reminder")
    db.commit()
    return {"ok": True}


class FeedbackIn(BaseModel):
    value: str = Field(pattern="^(up|down)$")


@router.post("/suggestions/{sid}/feedback", dependencies=auth)
def feedback(sid: int, body: FeedbackIn, db: Session = Depends(get_db)):
    sug = db.get(Suggestion, sid)
    if not sug:
        raise HTTPException(404, "Not found")
    sug.feedback = body.value
    record(db, f"Learned: a tip was {'useful' if body.value == 'up' else 'not useful'}", "suggestion")
    db.commit()
    return {"ok": True}


@router.post("/suggestions/refresh", dependencies=auth)
def refresh_suggestions(db: Session = Depends(get_db)):
    tips = briefing.refresh_suggestions(db)
    db.commit()
    return {"suggestions": tips}


class ToggleIn(BaseModel):
    enabled: bool


@router.post("/connections/{name}", dependencies=auth)
def toggle(name: str, body: ToggleIn, db: Session = Depends(get_db)):
    c = db.get(Connection, name)
    if not c:
        raise HTTPException(404, "Not found")
    c.enabled = body.enabled
    record(db, f"{'Turned on' if body.enabled else 'Paused'} {c.label}", "settings")
    db.commit()
    return {"ok": True}


@router.post("/briefing/{kind}", dependencies=auth)
def briefing_now(kind: str, db: Session = Depends(get_db)):
    if kind not in ("morning", "evening"):
        raise HTTPException(404, "Not found")
    text = briefing.send_briefing(db, kind)
    db.commit()
    return {"text": text}


# ---------- Google connect ----------
@router.get("/google/connect", dependencies=auth)
def google_connect(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    if not settings.google_ready:
        raise HTTPException(400, "Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env first")
    url = google_auth.start_url(db)
    db.commit()
    return RedirectResponse(url)


@router.get("/google/callback", dependencies=auth)
def google_callback(request: Request, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    # behind a proxy the app sees http; rebuild the URL Google actually called
    url = settings.public_url.rstrip("/") + request.url.path + ("?" + request.url.query if request.url.query else "")
    google_auth.finish(db, url)
    record(db, "Connected Gmail and Google Calendar", "settings")
    db.commit()
    return RedirectResponse("/#settings")


@router.post("/google/disconnect", dependencies=auth)
def google_disconnect(db: Session = Depends(get_db)):
    google_auth.disconnect(db)
    record(db, "Disconnected Google", "settings")
    db.commit()
    return {"ok": True}
