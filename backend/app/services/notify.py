"""Send a message to the owner on every channel that is switched on."""

import json
import logging

import httpx

from sqlalchemy.orm import Session

from ..config import get_settings
from ..integrations import telegram, whatsapp
from ..models import is_enabled, kv_get, kv_set

log = logging.getLogger("mrbob")


def telegram_chat(db: Session) -> str:
    """The owner's Telegram chat: from .env, or saved when he shared his contact."""
    return get_settings().telegram_chat_id or kv_get(db, "telegram_chat_id")


def push_tokens(db: Session) -> list[str]:
    try:
        return json.loads(kv_get(db, "expo_push_tokens", "[]"))
    except json.JSONDecodeError:
        return []


def add_push_token(db: Session, token: str) -> bool:
    tokens = push_tokens(db)
    if token in tokens:
        return False
    kv_set(db, "expo_push_tokens", json.dumps((tokens + [token])[-5:]))
    return True


def send_push(db: Session, text: str) -> None:
    """Phone app notification through Expo's free push service."""
    tokens = push_tokens(db)
    if not tokens:
        return
    first, _, rest = text.partition("\n")
    messages = [{"to": t, "title": first[:80] if rest else "Mr. Bob", "body": (rest or first)[:300],
                 "sound": "default", "priority": "high"} for t in tokens]
    r = httpx.post("https://exp.host/--/api/v2/push/send", json=messages, timeout=20)
    # forget phones that uninstalled the app
    dead = [m["to"] for m, res in zip(messages, r.json().get("data", []))
            if res.get("details", {}).get("error") == "DeviceNotRegistered"]
    if dead:
        kv_set(db, "expo_push_tokens", json.dumps([t for t in tokens if t not in dead]))


def notify(db: Session, text: str, *, voice: bytes = b"", caption: str = "") -> None:
    if is_enabled(db, "telegram"):
        chat = telegram_chat(db)
        if chat:
            try:
                telegram.send_text(text, chat)
                if voice:
                    telegram.send_voice(voice, chat, caption)
            except Exception as exc:
                log.warning("Telegram send failed: %s", exc)
    if is_enabled(db, "app"):
        try:
            send_push(db, text)
        except Exception as exc:
            log.warning("Phone push failed: %s", exc)
    if is_enabled(db, "whatsapp"):
        s = get_settings()
        try:
            if s.whatsapp_alerts_ready:
                whatsapp.send_alert(text)
            elif s.whatsapp_chat_ready and s.owner_phone:
                # Cloud API can only send free-form text if he messaged Mr. Bob in the last 24 hours
                whatsapp.send_text(s.owner_phone, text)
        except Exception as exc:
            log.warning("WhatsApp send failed: %s", exc)
