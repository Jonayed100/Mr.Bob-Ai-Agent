"""Google sign-in for Gmail and Calendar.

The owner clicks "Connect Google" on the dashboard once. Google sends him
back to /api/google/callback and we keep the refresh token in the database.
"""

import json
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import kv_get, kv_set

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",  # drafts only, Mr. Bob never sends
    "https://www.googleapis.com/auth/calendar.readonly",
]
TOKEN_KEY = "google_token"
VERIFIER_KEY = "google_code_verifier"


def _redirect_uri() -> str:
    return get_settings().public_url.rstrip("/") + "/api/google/callback"


def _flow() -> Flow:
    s = get_settings()
    if s.public_url.startswith("http://"):
        # allow plain http only while testing on your own computer
        os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
    config = {
        "web": {
            "client_id": s.google_client_id,
            "client_secret": s.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [_redirect_uri()],
        }
    }
    return Flow.from_client_config(config, scopes=SCOPES, redirect_uri=_redirect_uri())


def start_url(db: Session) -> str:
    flow = _flow()
    url, _state = flow.authorization_url(access_type="offline", prompt="consent", include_granted_scopes="true")
    verifier = getattr(flow, "code_verifier", None)
    kv_set(db, VERIFIER_KEY, verifier or "")
    return url


def finish(db: Session, full_callback_url: str) -> None:
    flow = _flow()
    verifier = kv_get(db, VERIFIER_KEY)
    if verifier:
        flow.code_verifier = verifier
    flow.fetch_token(authorization_response=full_callback_url)
    kv_set(db, TOKEN_KEY, flow.credentials.to_json())
    kv_set(db, VERIFIER_KEY, "")


def get_credentials(db: Session) -> Credentials | None:
    raw = kv_get(db, TOKEN_KEY)
    if not raw:
        return None
    creds = Credentials.from_authorized_user_info(json.loads(raw), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        kv_set(db, TOKEN_KEY, creds.to_json())
    return creds if creds.valid else None


def is_connected(db: Session) -> bool:
    return bool(kv_get(db, TOKEN_KEY))


def disconnect(db: Session) -> None:
    kv_set(db, TOKEN_KEY, "")
