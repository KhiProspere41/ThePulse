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


def _player_stats_job():
    """Load the next NFL season's player stats the first day they exist.

    nflverse cuts a player_stats release only once a season is over, on their
    own schedule outside this app's control — this can't "load 2025" on
    demand before that file exists, only notice the moment it does. The check
    itself only needs httpx (already a core dependency); the actual load
    needs pandas/nfl-data-py, imported lazily here so the main app doesn't
    require those heavier packages just to boot — only this job does, and
    only once a new season is actually found. See render.yaml for why
    they're still installed on every deploy anyway: without that, this job
    would detect a new season and then fail to load it.
    """
    from sqlalchemy import func

    from app import models
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        loaded = db.query(func.max(models.PlayerSeasonStats.season)).scalar()
    finally:
        db.close()

    try:
        from app.scripts.load_player_stats import _latest_available_season
        import datetime as dt

        published = _latest_available_season(dt.date.today().year)
    except Exception:
        logger.exception("Could not check nflverse for a new player-stats season — continuing.")
        return

    if published is None or (loaded is not None and published <= loaded):
        logger.info("Player stats up to date (published: %s, loaded: %s).", published, loaded)
        return

    logger.info("New player-stats season published: %d (had up to %s) — loading.", published, loaded)
    try:
        from app.scripts.load_player_stats import load_season

        load_season(published)
    except ImportError:
        logger.warning(
            "Season %d is published but nfl-data-py/pandas aren't installed — "
            "run `pip install -r requirements-data.txt && pip install --no-deps nfl-data-py` "
            "and restart to load it.",
            published,
        )
    except Exception:
        logger.exception("Failed to load player stats for season %d — will retry next check.", published)


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
    scheduler.add_job(
        _player_stats_job,
        "interval",
        hours=settings.player_stats_check_interval_hours,
        id="check_player_stats_season",
    )
    scheduler.start()
    logger.info(
        "Scheduler started: odds every %sh, futures every %sh, player-stats season check every %sh",
        settings.odds_refresh_interval_hours,
        settings.futures_refresh_interval_hours,
        settings.player_stats_check_interval_hours,
    )
    return scheduler
