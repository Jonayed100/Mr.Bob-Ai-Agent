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


def make_token(settings: Settings) -> str:
    return _signer(settings).sign(b"owner").decode()


def token_ok(token: str, settings: Settings) -> bool:
    try:
        return _signer(settings).unsign(token, max_age=MAX_AGE) == b"owner"
    except (BadSignature, SignatureExpired):
        return False


def require_login(request: Request, settings: Settings = Depends(get_settings)) -> None:
    token = request.cookies.get(COOKIE, "")
    if not token:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:]
    if not token or not token_ok(token, settings):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Please log in")
