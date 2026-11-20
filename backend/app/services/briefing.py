import json
import logging

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..agent.brain import get_brain
from ..agent.language import language_rule
from ..agent.prompts import BRIEFING_PROMPT, SUGGESTIONS_PROMPT
from ..config import get_settings
from ..models import Suggestion, kv_get
from ..voice.tts import speak_sync
from .activity import record
from .notify import notify
from .snapshot import today_snapshot

log = logging.getLogger("mrbob")


def refresh_suggestions(db: Session) -> list[str]:
    s = get_settings()
    rated = db.scalars(select(Suggestion).where(Suggestion.feedback.is_not(None)).order_by(Suggestion.id.desc()).limit(12))
    feedback = [{"tip": r.text, "was": "useful" if r.feedback == "up" else "not useful"} for r in rated]
    data = {"today": today_snapshot(db), "feedback": feedback}
    result = get_brain().complete_json(
        db,
        SUGGESTIONS_PROMPT.format(city=s.city, owner=s.owner_name, data=json.dumps(data, default=str, ensure_ascii=False)),
        max_tokens=300,
    )
    tips = [str(t).strip() for t in result.get("suggestions", []) if str(t).strip()][:3]
    if tips:
        db.execute(update(Suggestion).values(active=False))
        for t in tips:
            db.add(Suggestion(text=t[:400]))
        record(db, f"Made {len(tips)} new suggestions", "suggestion")
    return tips


def send_briefing(db: Session, kind: str = "morning") -> str:
    """kind = 'morning' or 'evening'. Sent to Telegram as text and a voice note."""
    s = get_settings()
    language = kv_get(db, "language", "auto")
    length = "Under 90 words." if kind == "morning" else "Under 70 words. Say what got done and what is tomorrow."
    if language == "auto":
        lang_rule = "Write in natural Banglish (Bangla in English letters, mixed with English)."
    else:
        lang_rule = language_rule(language)
    text = get_brain().complete(
        db,
        BRIEFING_PROMPT.format(
            owner=s.owner_name, kind=kind, lang_rule=lang_rule, length=length,
            data=json.dumps(today_snapshot(db), default=str, ensure_ascii=False),
        ),
        max_tokens=350,
    )
    if not text:
        return ""
    title = "☀️ Good morning!" if kind == "morning" else "🌙 Today's wrap-up"
    try:
        voice = speak_sync(text, language)
    except Exception as exc:
        log.warning("Briefing voice failed: %s", exc)
        voice = b""
    notify(db, f"{title}\n\n{text}", voice=voice, caption=title)
    record(db, f"Sent your {kind} briefing", "briefing")
    return text
