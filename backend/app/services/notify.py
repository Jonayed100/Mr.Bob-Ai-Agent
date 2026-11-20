"""Send a message to the owner on every channel that is switched on."""

import logging

from sqlalchemy.orm import Session

from ..config import get_settings
from ..integrations import telegram, whatsapp
from ..models import is_enabled, kv_get

log = logging.getLogger("mrbob")


def telegram_chat(db: Session) -> str:
    """The owner's Telegram chat: from .env, or saved when he shared his contact."""
    return get_settings().telegram_chat_id or kv_get(db, "telegram_chat_id")


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
