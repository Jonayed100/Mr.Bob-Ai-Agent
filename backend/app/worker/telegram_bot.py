"""Talk to Mr. Bob from Telegram: text messages and voice notes.

Runs in a background thread with long polling, so no webhook or open port is needed.

Linking your account: send /start, then tap "Share my number". If the number
matches OWNER_PHONE, Mr. Bob remembers this chat as yours. Anyone else is ignored.
"""

import json
import logging
import threading
import time

import httpx

from ..agent.brain import get_brain
from ..config import get_settings
from ..db import session_scope
from ..integrations import telegram
from ..integrations.whatsapp import digits
from ..models import is_enabled, kv_get, kv_set
from ..services.activity import record
from ..services.notify import telegram_chat
from ..voice import stt, tts

log = logging.getLogger("mrbob")


def _ask_for_contact(chat_id: str) -> None:
    s = get_settings()
    keyboard = {"keyboard": [[{"text": "📱 Share my number", "request_contact": True}]],
                "resize_keyboard": True, "one_time_keyboard": True}
    httpx.post(
        f"https://api.telegram.org/bot{s.telegram_bot_token}/sendMessage",
        data={"chat_id": chat_id, "text": "Hi! I'm Mr. Bob 🐱\nTap the button below so I can check it's really you.",
              "reply_markup": json.dumps(keyboard)},
        timeout=20,
    )


def _link_owner(msg: dict, chat_id: str) -> None:
    """The user shared a contact: link the chat if it is his own number and it matches OWNER_PHONE."""
    s = get_settings()
    contact = msg.get("contact") or {}
    own = contact.get("user_id") == (msg.get("from") or {}).get("id")
    matches = s.owner_phone and digits(contact.get("phone_number", "")).endswith(digits(s.owner_phone)[-10:])
    remove = json.dumps({"remove_keyboard": True})
    if own and matches:
        with session_scope() as db:
            kv_set(db, "telegram_chat_id", chat_id)
            record(db, "Linked your Telegram account", "settings")
        httpx.post(f"https://api.telegram.org/bot{s.telegram_bot_token}/sendMessage",
                   data={"chat_id": chat_id, "text": "Linked! ✅ From now on I'll message you here. Send me text or a voice note any time.",
                         "reply_markup": remove}, timeout=20)
    else:
        httpx.post(f"https://api.telegram.org/bot{s.telegram_bot_token}/sendMessage",
                   data={"chat_id": chat_id, "text": "Sorry, I only work for my owner.", "reply_markup": remove}, timeout=20)


def _handle(update: dict) -> None:
    s = get_settings()
    msg = update.get("message") or {}
    chat_id = str(msg.get("chat", {}).get("id", ""))
    if not chat_id:
        return

    with session_scope() as db:
        owner_chat = telegram_chat(db)

    if not owner_chat:
        if msg.get("contact"):
            _link_owner(msg, chat_id)
        elif s.owner_phone:
            _ask_for_contact(chat_id)
        else:
            telegram.send_text(f"Your chat id is {chat_id}. Put OWNER_PHONE (or TELEGRAM_CHAT_ID={chat_id}) in .env.", chat_id)
        return
    if chat_id != owner_chat:
        return  # not the owner: stay quiet

    with session_scope() as db:
        if not is_enabled(db, "telegram"):
            return
        language = kv_get(db, "language", "auto")
        voice = msg.get("voice") or msg.get("audio")
        if voice:
            audio = telegram.download_file(voice["file_id"])
            heard = stt.transcribe(db, audio, "note.ogg", seconds=float(voice.get("duration", 0)))
            if not heard:
                telegram.send_text("Sorry, I couldn't hear that. Try again?", chat_id)
                return
            answer = get_brain().reply(db, heard, language=language, channel="telegram", spoken=True)
            telegram.send_text(f"🗣 {heard}\n\n{answer}", chat_id)
            telegram.send_voice(tts.speak_sync(answer, language), chat_id)
            return
        text = (msg.get("text") or "").strip()
        if not text:
            return
        if text == "/start":
            telegram.send_text(f"Hi {s.owner_name}! Mr. Bob here. Send me a message or a voice note. 🐱", chat_id)
            return
        answer = get_brain().reply(db, text, language=language, channel="telegram")
        telegram.send_text(answer, chat_id)


def _loop() -> None:
    while True:
        try:
            with session_scope() as db:
                offset = int(kv_get(db, "telegram_offset", "0") or 0)
            for update in telegram.get_updates(offset):
                with session_scope() as db:
                    kv_set(db, "telegram_offset", str(update["update_id"] + 1))
                try:
                    _handle(update)
                except Exception:
                    log.exception("Could not handle a Telegram message")
        except Exception as exc:
            log.warning("Telegram polling problem: %s", exc)
            time.sleep(10)


def start() -> None:
    if not get_settings().telegram_ready:
        log.info("Telegram token not set, Telegram chat is off")
        return
    threading.Thread(target=_loop, name="telegram", daemon=True).start()
    log.info("Telegram bot listening")
