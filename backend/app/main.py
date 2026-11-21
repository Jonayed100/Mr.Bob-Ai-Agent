import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from . import __version__
from .api import router
from .config import get_settings
from .db import engine, init_db
from .worker import scheduler, telegram_bot

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("mrbob")

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    samples = {"change-me", "pick-a-strong-password", "change-me-to-a-long-random-string", "paste-a-long-random-string-here"}
    weak = s.dashboard_password in samples or s.secret_key in samples or len(s.secret_key) < 32 or len(s.dashboard_password) < 8
    if weak and s.public_url.startswith("https://"):
        # never go live on the internet with the sample password or key
        raise RuntimeError("Set a strong DASHBOARD_PASSWORD and a SECRET_KEY of 32+ characters in .env before going online.")
    if weak:
        log.warning("Using the sample password or key. Fine on your computer, change them before going online.")
    init_db()
    jobs = scheduler.start()
    telegram_bot.start()
    log.info("Mr. Bob is awake. Dashboard: %s", s.public_url)
    yield
    jobs.shutdown(wait=False)


app = FastAPI(title="Mr. Bob", version=__version__, lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # the page may use the microphone itself, nothing else may
    "Permissions-Policy": "microphone=(self), camera=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}


@app.middleware("http")
async def secure_responses(request: Request, call_next):
    try:
        response = await call_next(request)
    except Exception:
        log.exception("Unhandled error on %s %s", request.method, request.url.path)
        response = JSONResponse({"detail": "Something went wrong on Mr. Bob's side. Please try again."}, status_code=500)
    for key, value in SECURITY_HEADERS.items():
        response.headers.setdefault(key, value)
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


app.include_router(router)


@app.get("/health")
def health():
    """Used by Docker to check Mr. Bob is alive and can reach his database."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        log.exception("Health check: database unreachable")
        return JSONResponse({"ok": False, "database": "down", "version": __version__}, status_code=503)
    return {"ok": True, "database": "up", "version": __version__}


app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="dashboard")
