import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import SessionLocal, init_db
from app.ingest import refresh_all_leagues
from app.routers import elo, lines, odds, picks, stats
from app.scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    db = SessionLocal()
    try:
        refresh_all_leagues(db)
    except Exception:
        logger.exception("Initial odds fetch failed (check ODDS_API_KEY) — continuing without it.")
    finally:
        db.close()

    scheduler = start_scheduler()
    yield
    scheduler.shutdown()


app = FastAPI(title="ThePulse API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(odds.router)
app.include_router(lines.router)
app.include_router(picks.router)
app.include_router(stats.router)
app.include_router(elo.router)


@app.get("/health")
def health():
    return {"status": "ok"}
