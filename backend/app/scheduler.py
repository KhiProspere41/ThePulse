import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.database import SessionLocal
from app.ingest import refresh_all_leagues, update_closing_lines_and_clv

logger = logging.getLogger(__name__)


def _refresh_job():
    db = SessionLocal()
    try:
        refresh_all_leagues(db)
        update_closing_lines_and_clv(db)
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
    scheduler.start()
    logger.info("Scheduler started: refreshing odds every %sh", settings.odds_refresh_interval_hours)
    return scheduler
