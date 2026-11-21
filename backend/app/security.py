import hashlib
import hmac

from fastapi import Depends, HTTPException, Request, status
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner

from .config import Settings, get_settings

COOKIE = "mrbob_session"
MAX_AGE = 60 * 60 * 24 * 30  # stay logged in for 30 days


def _signer(settings: Settings) -> TimestampSigner:
    return TimestampSigner(settings.secret_key, salt="mrbob-login")


def password_ok(given: str, settings: Settings) -> bool:
    return hmac.compare_digest(given.encode(), settings.dashboard_password.encode())


def _subject(settings: Settings) -> bytes:
    """Tie every login to the current password, so changing it logs out every device."""
    tag = hashlib.sha256(settings.dashboard_password.encode()).hexdigest()[:16]
    return f"owner:{tag}".encode()


def make_token(settings: Settings) -> str:
    return _signer(settings).sign(_subject(settings)).decode()


def token_ok(token: str, settings: Settings) -> bool:
    try:
        return hmac.compare_digest(_signer(settings).unsign(token, max_age=MAX_AGE), _subject(settings))
    except (BadSignature, SignatureExpired):
        return False


def client_ip(request: Request) -> str:
    """The visitor's address (uvicorn already applies X-Forwarded-For from Caddy)."""
    return request.client.host if request.client else "unknown"


def require_login(request: Request, settings: Settings = Depends(get_settings)) -> None:
    token = request.cookies.get(COOKIE, "")
    if not token:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:]
    if not token or not token_ok(token, settings):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Please log in")
