"""Load a full NFL season schedule into `scheduled_games`, for the simulator.

The odds feed only ever shows the games the books have posted, so on its own it
can't answer "how many games will this team win?" — `app.simulate` would be
projecting a two-game season. This loads all 272 regular-season games,
including ones no book has priced yet.

    python -m app.scripts.load_schedule                 # season in progress
    python -m app.scripts.load_schedule --season 2026

Re-running is safe: rows are upserted by nflverse game id, so scores fill in as
the season goes.

Why not nfl-data-py, which the other loaders use? `import_schedules()` reads
from a single hard-coded mirror (`http://www.habitatring.com/games.csv`) with
no fallback, over plain HTTP, and that host is not always reachable — it 403s
from some networks outright. Since all this script needs is one CSV, it reads
nflverse's own copy over httpx (already a core dependency) and parses it with
the stdlib. That also means loading the schedule needs none of the heavyweight
data extras — no pandas, no pyarrow, no `--no-deps` install dance.
"""

import argparse
import csv
import datetime as dt
import io
import logging

import httpx

from app import models
from app.database import SessionLocal, init_db
from app.divisions import TEAM_TO_DIVISION, normalize
from app.simulate import current_season

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# nflverse's schedule dataset — the same file nfl-data-py's mirror serves,
# straight from the project that publishes it.
SCHEDULE_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"

REGULAR_SEASON = "REG"


def _int_or_none(value: str | None) -> int | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def fetch_rows(url: str = SCHEDULE_URL) -> list[dict]:
    logger.info("Fetching %s", url)
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
    return list(csv.DictReader(io.StringIO(response.text)))


def load_schedule(season: int, url: str = SCHEDULE_URL) -> int:
    init_db()
    rows = fetch_rows(url)

    db = SessionLocal()
    loaded = skipped = 0
    try:
        for row in rows:
            if _int_or_none(row.get("season")) != season:
                continue
            # Playoff games are simulated from the bracket, not replayed from
            # the schedule, so only regular-season rows belong here.
            if (row.get("game_type") or REGULAR_SEASON) != REGULAR_SEASON:
                continue

            home = normalize((row.get("home_team") or "").strip())
            away = normalize((row.get("away_team") or "").strip())
            if home not in TEAM_TO_DIVISION or away not in TEAM_TO_DIVISION:
                logger.warning("Skipping unrecognised matchup %s @ %s", away, home)
                skipped += 1
                continue

            game_id = (row.get("game_id") or f"{season}_{row.get('week')}_{away}_{home}").strip()
            game = db.get(models.ScheduledGame, game_id)
            if game is None:
                game = models.ScheduledGame(id=game_id)
                db.add(game)

            kickoff = None
            gameday = (row.get("gameday") or "").strip()
            if gameday:
                try:
                    kickoff = dt.datetime.fromisoformat(gameday)
                except ValueError:
                    kickoff = None

            game.season = season
            game.week = _int_or_none(row.get("week")) or 0
            game.kickoff = kickoff
            game.home_team = home
            game.away_team = away
            game.home_score = _int_or_none(row.get("home_score"))
            game.away_score = _int_or_none(row.get("away_score"))
            game.completed = game.home_score is not None and game.away_score is not None

            loaded += 1

        db.commit()
        logger.info(
            "Loaded %d regular-season games for %s (%d completed, %d skipped).",
            loaded,
            season,
            db.query(models.ScheduledGame)
            .filter(models.ScheduledGame.season == season, models.ScheduledGame.completed.is_(True))
            .count(),
            skipped,
        )
        return loaded
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=None, help="Season year, e.g. 2026")
    parser.add_argument("--url", default=SCHEDULE_URL, help="Override the schedule CSV source")
    args = parser.parse_args()
    load_schedule(args.season or current_season(), args.url)
