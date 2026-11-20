"""Speech to text.

OpenAI first (best with Bangla/English mixing), Groq's free Whisper as backup.
"""

import logging

from openai import OpenAI
from sqlalchemy.orm import Session

from ..config import get_settings
from ..services.costs import add_usage, stt_cost_usd

log = logging.getLogger("mrbob")

# a short hint helps the model with the names and mixed languages it will hear
PROMPT = "Mr. Bob, Jonayed, Dhaka, Gulshan, Banani, Mirpur, DESCO, bKash. Speech may mix Bangla and English."


def transcribe(db: Session, audio: bytes, filename: str, seconds: float = 0) -> str:
    s = get_settings()
    if s.openai_api_key:
        try:
            client = OpenAI(api_key=s.openai_api_key)
            res = client.audio.transcriptions.create(model=s.stt_model, file=(filename, audio), prompt=PROMPT)
            add_usage(db, "stt", seconds, stt_cost_usd(seconds))
            return (res.text or "").strip()
        except Exception as exc:  # fall through to the backup
            log.warning("OpenAI speech-to-text failed, trying Groq: %s", exc)
    if s.groq_api_key:
        client = OpenAI(api_key=s.groq_api_key, base_url="https://api.groq.com/openai/v1")
        res = client.audio.transcriptions.create(model=s.groq_stt_model, file=(filename, audio), prompt=PROMPT)
        return (res.text or "").strip()
    raise RuntimeError("No speech-to-text key set. Add OPENAI_API_KEY or GROQ_API_KEY to .env")
