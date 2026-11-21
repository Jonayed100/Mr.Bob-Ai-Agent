"""Answer the owner's WhatsApp messages (Cloud API webhook)."""

import logging
import threading

from ..agent.brain import get_brain
from ..agent.intent import wants_briefing
from ..config import get_settings
from ..db import session_scope
from ..integrations import whatsapp
from ..models import is_enabled, kv_get
from ..voice import stt, tts

log = logging.getLogger("mrbob")


def _answer(message: dict) -> None:
    s = get_settings()
    sender = message.get("from", "")
    if not s.owner_phone or whatsapp.digits(sender)[-10:] != whatsapp.digits(s.owner_phone)[-10:]:
        return  # only the owner
    with session_scope() as db:
        if not is_enabled(db, "whatsapp"):
            return
        language = kv_get(db, "language", "auto")
        kind = message.get("type")
        if kind == "text":
            text = message.get("text", {}).get("body", "").strip()
            if text and (text.lower() == "report" or wants_briefing(text)):
                from . import debrief

                report = debrief.build(db, said=text, language=language)
                whatsapp.send_text(sender, debrief.as_text(report))
                whatsapp.send_audio(sender, tts.speak_sync(debrief.spoken(report), report.language))
            elif text:
                whatsapp.send_text(sender, get_brain().reply(db, text, language=language, channel="whatsapp"))
        elif kind in ("audio", "voice"):
            media = message.get(kind, {})
            audio, mime = whatsapp.download_media(media["id"])
            ext = "ogg" if "ogg" in mime else "m4a" if "mp4" in mime else "mp3"
            heard = stt.transcribe(db, audio, f"note.{ext}")
            if not heard:
                whatsapp.send_text(sender, "Sorry, I couldn't hear that. Try again?")
                return
            if wants_briefing(heard):
                from . import debrief

                report = debrief.build(db, said=heard, language=language)
                whatsapp.send_text(sender, debrief.as_text(report))
                whatsapp.send_audio(sender, tts.speak_sync(debrief.spoken(report), report.language))
                return
            answer = get_brain().reply(db, heard, language=language, channel="whatsapp", spoken=True)
            whatsapp.send_text(sender, f"🗣 {heard}\n\n{answer}")
            whatsapp.send_audio(sender, tts.speak_sync(answer, language))
        else:
            whatsapp.send_text(sender, "I can read text and listen to voice notes for now. 🐱")


def handle_webhook(payload: dict) -> None:
    """Reply in the background so Meta gets its 200 OK right away."""
    for message in whatsapp.incoming_messages(payload):
        def run(m=message):
            try:
                _answer(m)
            except Exception:
                log.exception("Could not answer a WhatsApp message")

        threading.Thread(target=run, daemon=True).start()
