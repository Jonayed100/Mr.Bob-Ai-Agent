import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api import router
from .config import get_settings
from .db import init_db
from .worker import scheduler, telegram_bot

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("mrbob")

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    if s.dashboard_password == "change-me" or s.secret_key.startswith("change-me"):
        log.warning("Set DASHBOARD_PASSWORD and SECRET_KEY in .env before putting Mr. Bob online!")
    init_db()
    jobs = scheduler.start()
    telegram_bot.start()
    log.info("Mr. Bob is awake. Dashboard: %s", s.public_url)
    yield
    jobs.shutdown(wait=False)


app = FastAPI(title="Mr. Bob", version="0.1.0", lifespan=lifespan, docs_url=None, redoc_url=None)
app.include_router(router)


@app.get("/health")
def health():
    return {"ok": True}


app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="dashboard")
