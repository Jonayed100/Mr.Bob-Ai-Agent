"""Keep freshly spoken replies for a few minutes so the phone app can stream them by URL."""

import secrets
import threading
import time

TTL = 300  # seconds
_store: dict[str, tuple[float, bytes]] = {}
_lock = threading.Lock()


def put(mp3: bytes) -> str:
    key = secrets.token_urlsafe(18)
    now = time.time()
    with _lock:
        for k in [k for k, (t, _) in _store.items() if now - t > TTL]:
            del _store[k]
        _store[key] = (now, mp3)
    return key


def get(key: str) -> bytes | None:
    with _lock:
        item = _store.get(key)
    if not item or time.time() - item[0] > TTL:
        return None
    return item[1]
