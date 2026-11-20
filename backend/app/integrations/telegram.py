"""Small Telegram Bot API client (just the calls Mr. Bob needs)."""

import shutil
import subprocess
import tempfile
from pathlib import Path

import httpx

from ..config import get_settings


def _api(method: str) -> str:
    return f"https://api.telegram.org/bot{get_settings().telegram_bot_token}/{method}"


def send_text(text: str, chat_id: str | None = None) -> None:
    s = get_settings()
    chat = chat_id or s.telegram_chat_id
    if not (s.telegram_ready and chat):
        return
    httpx.post(_api("sendMessage"), data={"chat_id": chat, "text": text[:4000]}, timeout=20)


def send_voice(mp3: bytes, chat_id: str | None = None, caption: str = "") -> None:
    """Send audio as a Telegram voice note (needs ffmpeg), or as a normal audio file."""
    s = get_settings()
    chat = chat_id or s.telegram_chat_id
    if not (s.telegram_ready and chat and mp3):
        return
    ogg = mp3_to_ogg(mp3)
    if ogg:
        httpx.post(_api("sendVoice"), data={"chat_id": chat}, files={"voice": ("bob.ogg", ogg, "audio/ogg")}, timeout=60)
    else:
        httpx.post(
            _api("sendAudio"),
            data={"chat_id": chat, "title": "Mr. Bob", "caption": caption[:900]},
            files={"audio": ("bob.mp3", mp3, "audio/mpeg")},
            timeout=60,
        )


def get_updates(offset: int, timeout: int = 25) -> list[dict]:
    r = httpx.get(_api("getUpdates"), params={"offset": offset, "timeout": timeout}, timeout=timeout + 10)
    r.raise_for_status()
    return r.json().get("result", [])


def download_file(file_id: str) -> bytes:
    info = httpx.get(_api("getFile"), params={"file_id": file_id}, timeout=20).json()
    path = info["result"]["file_path"]
    token = get_settings().telegram_bot_token
    return httpx.get(f"https://api.telegram.org/file/bot{token}/{path}", timeout=60).content


def mp3_to_ogg(mp3: bytes) -> bytes | None:
    if not shutil.which("ffmpeg"):
        return None
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = Path(tmp, "in.mp3"), Path(tmp, "out.ogg")
        src.write_bytes(mp3)
        done = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-c:a", "libopus", "-b:a", "32k", str(dst)],
            capture_output=True,
            timeout=60,
        )
        return dst.read_bytes() if done.returncode == 0 and dst.exists() else None
