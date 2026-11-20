"""Text to speech with Microsoft Edge neural voices (free, includes Bangla)."""

import asyncio
import logging
import re

import edge_tts

from ..agent.language import reply_style
from ..config import get_settings

log = logging.getLogger("mrbob")


def voice_for(style: str) -> str:
    s = get_settings()
    return {"bangla": s.tts_voice_bangla, "banglish": s.tts_voice_banglish}.get(style, s.tts_voice_english)


def _clean(text: str) -> str:
    text = re.sub(r"[*_#`>]+", "", text)  # drop markdown symbols so they aren't read out
    return text.strip()[:2500]


async def speak(text: str, language: str | None = "auto") -> bytes:
    """Return MP3 bytes, or b'' if the voice service is unreachable."""
    text = _clean(text)
    if not text:
        return b""
    voice = voice_for(reply_style(text, language))
    audio = bytearray()
    try:
        async for chunk in edge_tts.Communicate(text, voice, rate="+4%").stream():
            if chunk["type"] == "audio":
                audio.extend(chunk["data"])
    except Exception as exc:
        log.warning("Voice failed (%s): %s", voice, exc)
        return b""
    return bytes(audio)


def speak_sync(text: str, language: str | None = "auto") -> bytes:
    """For background jobs that are not async."""
    return asyncio.run(speak(text, language))
