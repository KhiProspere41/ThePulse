import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import SessionLocal
from app.ingest import refresh_all_leagues
from app.routers import elo, futures, lines, odds, picks, player_stats, props, slips, stats
from app.scheduler import start_scheduler
from app.scripts.migrate import migrate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    migrate()

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
app.include_router(props.router)
app.include_router(futures.router)
app.include_router(player_stats.router)
app.include_router(slips.router)


@app.get("/health")
def health():
    return {"status": "ok"}
