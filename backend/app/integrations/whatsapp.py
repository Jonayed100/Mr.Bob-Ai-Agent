"""WhatsApp.

Two ways, use one or both:
1. Alerts (free, one-way): CallMeBot sends messages to your own WhatsApp number.
2. Chat (optional, two-way): Meta's WhatsApp Cloud API. You message Mr. Bob's
   WhatsApp number and he answers, including voice notes.
"""

import logging

import httpx

from ..config import get_settings

log = logging.getLogger("mrbob")


def digits(phone: str) -> str:
    return "".join(c for c in phone or "" if c.isdigit())


# ---------- 1. CallMeBot alerts ----------
def send_alert(text: str) -> None:
    s = get_settings()
    if not s.whatsapp_alerts_ready:
        return
    r = httpx.get(
        "https://api.callmebot.com/whatsapp.php",
        params={"phone": "+" + digits(s.owner_phone), "text": text[:1500], "apikey": s.callmebot_apikey},
        timeout=30,
    )
    if r.status_code >= 400:
        log.warning("CallMeBot said %s: %s", r.status_code, r.text[:200])


# ---------- 2. Cloud API chat ----------
def _graph(path: str) -> str:
    s = get_settings()
    return f"https://graph.facebook.com/{s.whatsapp_graph_version}/{path}"


def _headers() -> dict:
    return {"Authorization": f"Bearer {get_settings().whatsapp_token}"}


def send_text(to: str, text: str) -> None:
    s = get_settings()
    if not s.whatsapp_chat_ready:
        return
    httpx.post(
        _graph(f"{s.whatsapp_phone_number_id}/messages"),
        headers=_headers(),
        json={"messaging_product": "whatsapp", "to": digits(to), "type": "text", "text": {"body": text[:4000]}},
        timeout=30,
    ).raise_for_status()


def send_audio(to: str, mp3: bytes) -> None:
    s = get_settings()
    if not (s.whatsapp_chat_ready and mp3):
        return
    up = httpx.post(
        _graph(f"{s.whatsapp_phone_number_id}/media"),
        headers=_headers(),
        data={"messaging_product": "whatsapp", "type": "audio/mpeg"},
        files={"file": ("bob.mp3", mp3, "audio/mpeg")},
        timeout=60,
    )
    up.raise_for_status()
    httpx.post(
        _graph(f"{s.whatsapp_phone_number_id}/messages"),
        headers=_headers(),
        json={"messaging_product": "whatsapp", "to": digits(to), "type": "audio", "audio": {"id": up.json()["id"]}},
        timeout=30,
    ).raise_for_status()


def download_media(media_id: str) -> tuple[bytes, str]:
    info = httpx.get(_graph(media_id), headers=_headers(), timeout=20).json()
    data = httpx.get(info["url"], headers=_headers(), timeout=60).content
    return data, info.get("mime_type", "audio/ogg")


def incoming_messages(payload: dict) -> list[dict]:
    """Pull the messages out of a Cloud API webhook payload."""
    out = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for m in change.get("value", {}).get("messages", []) or []:
                out.append(m)
    return out
