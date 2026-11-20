"""Talk to Mr. Bob from Telegram: text messages and voice notes.

Runs in a background thread with long polling, so no webhook or open port is needed.
Only the owner's chat (TELEGRAM_CHAT_ID) gets answers.
"""

import logging
import threading
import time

from ..agent.brain import get_brain
from ..config import get_settings
from ..db import session_scope
from ..integrations import telegram
from ..models import is_enabled, kv_get, kv_set
from ..voice import stt, tts

log = logging.getLogger("mrbob")


def _handle(update: dict) -> None:
    s = get_settings()
    msg = update.get("message") or {}
    chat_id = str(msg.get("chat", {}).get("id", ""))
    if not chat_id:
        return
    if not s.telegram_chat_id:
        telegram.send_text(
            f"Hi! I'm Mr. Bob. Your chat id is {chat_id}.\nPut TELEGRAM_CHAT_ID={chat_id} in the .env file and restart me.",
            chat_id,
        )
        return
    if chat_id != s.telegram_chat_id:
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
            telegram.send_text("Hi Jonayed! Mr. Bob here. Send me a message or a voice note. 🐱", chat_id)
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
