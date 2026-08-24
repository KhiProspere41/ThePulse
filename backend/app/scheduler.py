import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.database import SessionLocal
from app.ingest import ingest_futures, refresh_all_leagues, update_closing_lines_and_clv

logger = logging.getLogger(__name__)


def _refresh_job():
    db = SessionLocal()
    try:
        refresh_all_leagues(db)
        update_closing_lines_and_clv(db)
    finally:
        db.close()


def _futures_job():
    """Super Bowl outrights. Split out from the odds job because futures move
    slowly and each refresh costs an API credit — on the free tier, polling
    them every two hours alongside game lines would spend ~360 of the monthly
    500 on a market that barely changes day to day.

    Player props are deliberately absent from the scheduler entirely: they are
    billed per market *per event*, so warming all of them would cost more than
    the whole monthly allowance in a couple of days. They're fetched on demand
    and cached instead (see `ingest.ingest_player_props`).
    """
    db = SessionLocal()
    try:
        ingest_futures(db)
    except Exception:
        logger.exception("Futures refresh failed — continuing.")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _refresh_job,
        "interval",
        hours=settings.odds_refresh_interval_hours,
        id="refresh_odds",
    )
    scheduler.add_job(
        _futures_job,
        "interval",
        hours=settings.futures_refresh_interval_hours,
        id="refresh_futures",
    )
    scheduler.start()
    logger.info(
        "Scheduler started: odds every %sh, futures every %sh",
        settings.odds_refresh_interval_hours,
        settings.futures_refresh_interval_hours,
    )
    return scheduler
