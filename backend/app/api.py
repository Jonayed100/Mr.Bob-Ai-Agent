import asyncio
import base64
import hashlib
import hmac
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import PlainTextResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from .agent.brain import get_brain
from .agent.intent import wants_briefing
from .config import Settings, get_settings
from .db import get_db
from .integrations import google_auth
from .models import Activity, Connection, Memory, Message, Reminder, Report, Suggestion, kv_get, kv_set
from .ratelimit import login_guard
from .security import COOKIE, MAX_AGE, client_ip, make_token, password_ok, require_login
from .services import briefing, costs, debrief, memory, money, reminder_jobs, snapshot
from .services.reminders import PRIORITIES, REPEATS, clean_choice
from .services.notify import telegram_chat
from .services.whatsapp_chat import handle_webhook
from .services.activity import record
from .timeutil import clock, friendly, hhmm, now_local, now_utc, to_utc
from .voice import audio_cache, stt, tts

router = APIRouter(prefix="/api")
auth = [Depends(require_login)]
LANGS = {"auto", "english", "bangla", "banglish"}
MAX_VOICE_BYTES = 8 * 1024 * 1024  # about 8 MB, far more than a one-minute voice note


# ---------- login ----------
class LoginIn(BaseModel):
    password: str = Field(max_length=200)


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, settings: Settings = Depends(get_settings)):
    ip = client_ip(request)
    wait = login_guard.retry_after(ip)
    if wait:
        minutes = max(1, round(wait / 60))
        raise HTTPException(429, f"Too many wrong tries. Try again in {minutes} min.", headers={"Retry-After": str(wait)})
    if not password_ok(body.password, settings):
        login_guard.failed(ip)
        raise HTTPException(401, "Wrong password")
    login_guard.succeeded(ip)
    response.set_cookie(
        COOKIE, make_token(settings), max_age=MAX_AGE, httponly=True, samesite="lax",
        secure=settings.public_url.startswith("https://"),
    )
    # the phone app keeps this token and sends it as "Authorization: Bearer ..."
    return {"ok": True, "token": make_token(settings)}


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
        "now": {"day": now.strftime("%A").upper(), "date": now.day, "time": clock(now)},
        "weather": snapshot.cached_weather() or snapshot.refresh_weather(),
        "events": snapshot.events(db, 0),
        "reminders": [reminder_jobs.serialize(r) for r in db.scalars(
            select(Reminder).where(Reminder.done.is_(False)).order_by(Reminder.due_at.is_(None), Reminder.due_at).limit(20))],
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
        "telegram": {"ready": settings.telegram_ready, "chat_set": bool(telegram_chat(db))},
        "whatsapp": {"alerts": settings.whatsapp_alerts_ready, "chat": settings.whatsapp_chat_ready},
        "bkash": money.month_summary(db),
        "activity": [{"time": hhmm(a.created_at), "text": a.text} for a in activity],
        "cost": costs.month_summary(db),
        "due_now": [reminder_jobs.serialize(r) for r in db.scalars(
            select(Reminder).where(Reminder.seen_on_web.is_(False), Reminder.notified_at.is_not(None)))],
        "counts": {
            "reminders_open": db.query(Reminder).filter(Reminder.done.is_(False)).count(),
            "memories": db.query(Memory).count(),
            "reports": db.query(Report).count(),
        },
        "latest_report": (lambda r: debrief.to_dict(r) if r else None)(
            db.scalars(select(Report).order_by(Report.id.desc()).limit(1)).first()),
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


async def _speak(db: Session, text: str, language: str) -> bytes:
    mp3, provider = await tts.speak_ex(text, language)
    if mp3 and provider == "openai":
        secs = len(text.split()) / 2.5  # about 150 words a minute
        costs.add_usage(db, "tts", secs, costs.tts_cost_usd(secs))
    return mp3


async def _briefing_response(db: Session, said: str, language: str, heard: str = "") -> dict:
    """Build tonight's report and voice each part separately, so the page can play it part by part."""
    report = await run_in_threadpool(debrief.build, db, said=said, language=language)
    data = debrief.to_dict(report)
    # voice all parts at the same time so the briefing starts quickly
    clips = await asyncio.gather(
        *[_speak(db, f"{p['title']}. {p['text']}", report.language) for p in data["parts"]],
        _speak(db, data["summary"], report.language) if data["summary"] else asyncio.sleep(0, b""),
    )
    for part, mp3 in zip(data["parts"], clips):
        part["audio"] = base64.b64encode(mp3).decode() if mp3 else None
        part["audio_url"] = f"/api/audio/{audio_cache.put(mp3)}.mp3" if mp3 else None
    intro = clips[-1] or b""
    db.commit()
    return _with_audio({"mode": "briefing", "heard": heard, "reply": data["summary"], "report": data}, intro)


@router.post("/chat", dependencies=auth)
async def chat(body: ChatIn, db: Session = Depends(get_db)):
    language = _lang(db, body.language)
    text = body.text.strip()
    if wants_briefing(text):
        return await _briefing_response(db, text, language)
    answer = await run_in_threadpool(get_brain().reply, db, text, language=language, channel="web", spoken=body.speak)
    db.commit()
    audio = await _speak(db, answer, language) if body.speak else b""
    db.commit()
    return _with_audio({"mode": "chat", "reply": answer}, audio)


@router.post("/voice", dependencies=auth)
async def voice(
    audio: UploadFile = File(...),
    seconds: float = Form(0),
    language: str = Form("auto"),
    db: Session = Depends(get_db),
):
    data = await audio.read(MAX_VOICE_BYTES + 1)
    if len(data) > MAX_VOICE_BYTES:
        raise HTTPException(413, "That recording is too long. Keep it under a minute.")
    if len(data) < 800:
        raise HTTPException(400, "That recording was too short")
    language = _lang(db, language)
    heard = await run_in_threadpool(stt.transcribe, db, data, audio.filename or "voice.webm", seconds)
    if not heard:
        db.commit()
        return {"mode": "chat", "heard": "", "reply": "Sorry, I couldn't hear that. Try again?", "audio": None}
    if wants_briefing(heard):
        return await _briefing_response(db, heard, language, heard)
    answer = await run_in_threadpool(get_brain().reply, db, heard, language=language, channel="voice", spoken=True)
    db.commit()
    mp3 = await _speak(db, answer, language)
    db.commit()
    return _with_audio({"mode": "chat", "heard": heard, "reply": answer}, mp3)


class SpeakIn(BaseModel):
    text: str = Field(min_length=1, max_length=3000)
    language: str = "auto"


@router.post("/tts", dependencies=auth)
async def speak_text(body: SpeakIn, db: Session = Depends(get_db)):
    """Read any text aloud in Mr. Bob's voice (used to replay reports and reminders)."""
    mp3 = await _speak(db, body.text, body.language)
    db.commit()
    return _with_audio({}, mp3)


def _with_audio(body: dict, mp3: bytes) -> dict:
    """The web page plays base64 audio; the phone app streams it from a short-lived link."""
    body["audio"] = base64.b64encode(mp3).decode() if mp3 else None
    body["audio_url"] = f"/api/audio/{audio_cache.put(mp3)}.mp3" if mp3 else None
    return body


@router.get("/audio/{key}.mp3")
def audio(key: str):
    mp3 = audio_cache.get(key)
    if mp3 is None:
        raise HTTPException(404, "Expired")
    return Response(mp3, media_type="audio/mpeg")


@router.get("/messages", dependencies=auth)
def messages(db: Session = Depends(get_db)):
    rows = db.scalars(select(Message).order_by(Message.id.desc()).limit(30)).all()
    return [{"role": m.role, "text": m.content, "channel": m.channel} for m in reversed(rows)]


# ---------- reminders ----------
class ReminderIn(BaseModel):
    text: str = Field(min_length=1, max_length=300)
    due_at: datetime | None = None
    priority: str = "normal"
    repeat: str = "none"
    notes: str = Field("", max_length=1000)


class ReminderPatch(BaseModel):
    text: str | None = Field(None, min_length=1, max_length=300)
    due_at: datetime | None = None
    clear_time: bool = False
    priority: str | None = None
    repeat: str | None = None
    notes: str | None = Field(None, max_length=1000)
    done: bool | None = None


@router.get("/due", dependencies=auth)
def due_now(db: Session = Depends(get_db)):
    """Light, frequent check from the website for reminders that just went off."""
    rows = db.scalars(select(Reminder).where(Reminder.seen_on_web.is_(False), Reminder.notified_at.is_not(None))).all()
    return [reminder_jobs.serialize(r) for r in rows]


@router.get("/reminders", dependencies=auth)
def list_reminders(db: Session = Depends(get_db)):
    rows = db.scalars(select(Reminder).order_by(Reminder.done, Reminder.due_at.is_(None), Reminder.due_at)).all()
    return [reminder_jobs.serialize(r) for r in rows]


@router.post("/reminders", dependencies=auth)
def add_reminder(body: ReminderIn, db: Session = Depends(get_db)):
    r = Reminder(
        text=body.text.strip(), notes=body.notes.strip(), due_at=to_utc(body.due_at) if body.due_at else None,
        priority=clean_choice(body.priority, PRIORITIES, "normal"), repeat=clean_choice(body.repeat, REPEATS, "none"),
    )
    db.add(r)
    db.flush()
    record(db, f"Added reminder: {r.text}" + (f" ({friendly(r.due_at)})" if r.due_at else ""), "reminder")
    db.commit()
    return reminder_jobs.serialize(r)


@router.patch("/reminders/{rid}", dependencies=auth)
def edit_reminder(rid: int, body: ReminderPatch, db: Session = Depends(get_db)):
    r = db.get(Reminder, rid)
    if not r:
        raise HTTPException(404, "Not found")
    if body.text is not None:
        r.text = body.text.strip()
    if body.notes is not None:
        r.notes = body.notes.strip()
    if body.priority is not None:
        r.priority = clean_choice(body.priority, PRIORITIES, r.priority)
    if body.repeat is not None:
        r.repeat = clean_choice(body.repeat, REPEATS, r.repeat)
    if body.clear_time:
        r.due_at, r.notified = None, False
    elif body.due_at is not None:
        r.due_at, r.notified = to_utc(body.due_at), False
    if body.done is not None:
        r.done = body.done
        r.done_at = now_utc() if body.done else None
        r.seen_on_web = True
        if body.done:
            record(db, f"Completed: {r.text}", "reminder")
    db.commit()
    return reminder_jobs.serialize(r)


@router.delete("/reminders/{rid}", dependencies=auth)
def delete_reminder(rid: int, db: Session = Depends(get_db)):
    r = db.get(Reminder, rid)
    if not r:
        raise HTTPException(404, "Not found")
    db.delete(r)
    record(db, f"Deleted reminder: {r.text}", "reminder")
    db.commit()
    return {"ok": True}


@router.post("/reminders/{rid}/seen", dependencies=auth)
def reminder_seen(rid: int, db: Session = Depends(get_db)):
    r = db.get(Reminder, rid)
    if r:
        r.seen_on_web = True
        db.commit()
    return {"ok": True}


class SnoozeIn(BaseModel):
    minutes: int = Field(10, ge=1, le=24 * 60)


@router.post("/reminders/{rid}/snooze", dependencies=auth)
def snooze(rid: int, body: SnoozeIn, db: Session = Depends(get_db)):
    r = db.get(Reminder, rid)
    if not r:
        raise HTTPException(404, "Not found")
    r.due_at, r.notified, r.seen_on_web, r.done = now_utc() + timedelta(minutes=body.minutes), False, True, False
    record(db, f"Snoozed {body.minutes} min: {r.text}", "reminder")
    db.commit()
    return reminder_jobs.serialize(r)


# ---------- memory ----------
class MemoryIn(BaseModel):
    text: str = Field(min_length=2, max_length=400)
    kind: str = "fact"


@router.get("/memories", dependencies=auth)
def list_memories(db: Session = Depends(get_db)):
    return [memory.to_dict(m) for m in db.scalars(select(Memory).order_by(Memory.id.desc()))]


@router.post("/memories", dependencies=auth)
def add_memory(body: MemoryIn, db: Session = Depends(get_db)):
    m = memory.add(db, body.text, body.kind, source="manual")
    db.commit()
    if not m:
        raise HTTPException(409, "Already remembered (or not allowed to store)")
    return memory.to_dict(m)


@router.delete("/memories/{mid}", dependencies=auth)
def delete_memory(mid: int, db: Session = Depends(get_db)):
    m = db.get(Memory, mid)
    if not m:
        raise HTTPException(404, "Not found")
    db.delete(m)
    record(db, f"Forgot: {m.text[:80]}", "memory")
    db.commit()
    return {"ok": True}


# ---------- reports ----------
@router.get("/reports", dependencies=auth)
def list_reports(db: Session = Depends(get_db)):
    return [debrief.to_dict(r) for r in db.scalars(select(Report).order_by(Report.id.desc()).limit(60))]


@router.get("/reports/{rid}", dependencies=auth)
def get_report(rid: int, db: Session = Depends(get_db)):
    r = db.get(Report, rid)
    if not r:
        raise HTTPException(404, "Not found")
    return debrief.to_dict(r)


@router.delete("/reports/{rid}", dependencies=auth)
def delete_report(rid: int, db: Session = Depends(get_db)):
    r = db.get(Report, rid)
    if r:
        db.delete(r)
        db.commit()
    return {"ok": True}


class BriefIn(BaseModel):
    language: str = "auto"
    said: str = ""


@router.post("/briefing/tonight", dependencies=auth)
async def briefing_tonight(body: BriefIn, db: Session = Depends(get_db)):
    """The night briefing, voiced part by part, and saved to Reports."""
    return await _briefing_response(db, body.said or "Tell me about my important tasks", _lang(db, body.language))


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


# ---------- bKash SMS (called by the SMS forwarder app on your phone) ----------
@router.post("/sms")
async def sms_webhook(request: Request, token: str = "", db: Session = Depends(get_db),
                      settings: Settings = Depends(get_settings)):
    if not settings.sms_webhook_token or not hmac.compare_digest(token, settings.sms_webhook_token):
        raise HTTPException(403, "Bad token")
    try:
        body = await request.json()
    except Exception:
        body = dict(await request.form())
    sender = str(body.get("from") or body.get("sender") or body.get("number") or "")
    text = str(body.get("text") or body.get("message") or body.get("body") or body.get("content") or "")
    tx = money.record_sms(db, sender, text)
    db.commit()
    return {"ok": True, "saved": bool(tx)}


# ---------- WhatsApp Cloud API webhook ----------
@router.get("/whatsapp/webhook")
def whatsapp_verify(request: Request, settings: Settings = Depends(get_settings)):
    q = request.query_params
    if q.get("hub.mode") == "subscribe" and settings.whatsapp_verify_token and \
            q.get("hub.verify_token") == settings.whatsapp_verify_token:
        return PlainTextResponse(q.get("hub.challenge", ""))
    raise HTTPException(403, "Verification failed")


@router.post("/whatsapp/webhook")
async def whatsapp_incoming(request: Request, settings: Settings = Depends(get_settings)):
    raw = await request.body()
    if settings.whatsapp_app_secret:
        expected = "sha256=" + hmac.new(settings.whatsapp_app_secret.encode(), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, request.headers.get("x-hub-signature-256", "")):
            raise HTTPException(403, "Bad signature")
    try:
        handle_webhook(await request.json())
    except Exception:
        pass  # always answer 200 so Meta doesn't keep retrying
    return {"ok": True}


# ---------- phone app push notifications ----------
class PushIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)


@router.post("/push/register", dependencies=auth)
def push_register(body: PushIn, db: Session = Depends(get_db)):
    from .services.notify import add_push_token

    if add_push_token(db, body.token):
        record(db, "Phone app connected for notifications", "settings")
    db.commit()
    return {"ok": True}
