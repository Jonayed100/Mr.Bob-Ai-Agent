"""Text to speech with Microsoft Edge neural voices (free, includes Bangla)."""

import asyncio
import logging
import re

import edge_tts
from openai import AsyncOpenAI

from ..agent.language import reply_style
from ..config import get_settings

log = logging.getLogger("mrbob")


def voice_for(style: str) -> str:
    s = get_settings()
    return {"bangla": s.tts_voice_bangla, "banglish": s.tts_voice_banglish}.get(style, s.tts_voice_english)


def _clean(text: str) -> str:
    text = re.sub(r"[*_#`>]+", "", text)  # drop markdown symbols so they aren't read out
    return text.strip()[:2500]


VOICE_STYLE = (
    "You are Mr. Bob, a warm, calm and caring personal assistant who is also a good friend. "
    "Speak naturally, like a real person: relaxed pace, gentle smile in the voice, clear pauses between ideas, "
    "slight emphasis on times, deadlines and anything important. Never sound robotic or rushed."
)


def _openai_for(style: str) -> bool:
    s = get_settings()
    if not s.openai_api_key or s.tts_provider != "openai":
        return False
    # Bangla script sounds most natural with the native Bangladeshi voice unless told otherwise
    return style != "bangla" or s.tts_bangla_provider == "openai"


async def _openai(text: str, style: str) -> bytes:
    s = get_settings()
    client = AsyncOpenAI(api_key=s.openai_api_key)
    lang_hint = {"bangla": " Speak in Bangla with a natural Bangladeshi accent.",
                 "banglish": " The text mixes Bangla and English the way people in Dhaka talk; pronounce the Bangla words naturally."}
    res = await client.audio.speech.create(
        model=s.tts_model, voice=s.tts_openai_voice, input=text[:3500],
        instructions=VOICE_STYLE + lang_hint.get(style, ""), response_format="mp3",
    )
    return res.content


async def speak(text: str, language: str | None = "auto") -> bytes:
    return (await speak_ex(text, language))[0]


async def speak_ex(text: str, language: str | None = "auto") -> tuple[bytes, str]:
    """Return (MP3 bytes, provider). Bytes are b'' if every voice service is unreachable.

    Uses OpenAI's expressive voice when available, and Microsoft's free neural
    voices (including native Bangla) otherwise or as a backup.
    """
    text = _clean(text)
    if not text:
        return b"", ""
    style = reply_style(text, language)
    if _openai_for(style):
        try:
            return await _openai(text, style), "openai"
        except Exception as exc:
            log.warning("Expressive voice failed, using backup voice: %s", exc)
    voice = voice_for(style)
    audio = bytearray()
    try:
        async for chunk in edge_tts.Communicate(text, voice, rate="+4%").stream():
            if chunk["type"] == "audio":
                audio.extend(chunk["data"])
    except Exception as exc:
        log.warning("Voice failed (%s): %s", voice, exc)
        return b"", ""
    return bytes(audio), "edge"


def speak_sync(text: str, language: str | None = "auto") -> bytes:
    """For background jobs that are not async."""
    return asyncio.run(speak(text, language))
